import hashlib
import logging
import posixpath
import time
import urllib.parse
from abc import ABC
from datetime import datetime
from ipaddress import IPv4Address
from typing import Literal, Final, final, Any

import aiohttp
from aenum import StrEnum

_LOGGER = logging.getLogger(__name__)


DEFAULT_PRINTER_PORT: Final[int] = 10800
DEFAULT_CAMERA_PORT: Final[int] = 30
APIDataResponse = dict[str, Any]


async def on_request_start(session, context, params):
    logging.getLogger("aiohttp.client").debug("Starting request <%s>", params)


def create_aiohttp_session():
    trace_config = aiohttp.TraceConfig()
    trace_config.on_request_start.append(on_request_start)
    return aiohttp.ClientSession(trace_configs=[trace_config])


class APIResponseError(aiohttp.ClientResponseError):
    """Raise3D API response error."""


class JobActionValue(StrEnum):
    PAUSE = "pause"
    RESUME = "resume"
    STOP = "stop"


class RunningStatusValue(StrEnum):
    IDLE = "idle"
    PAUSED = "paused"
    RUNNING = "running"
    BUSY = "busy"
    COMPLETED = "completed"
    ERROR = "error"


class JobStatusValue(StrEnum):
    PAUSED = "paused"
    RUNNING = "running"
    COMPLETED = "completed"
    STOPPED = "stopped"


class Raise3DAPIBase(ABC):
    __slots__ = ("_session", "logger")

    def __init__(
        self,
        session: aiohttp.ClientSession | None = None,
        logger: logging.Logger | logging.LoggerAdapter = _LOGGER,
        *args,
        **kwargs,
    ) -> None:
        self._session = session or create_aiohttp_session()
        self.logger = logger

    @property
    def session(self) -> aiohttp.ClientSession:
        return self._session

    async def close(self) -> None:
        await self._session.close()


class Raise3DCameraAPI(Raise3DAPIBase):
    def __init__(
        self,
        *args,
        camera_url: str,
        camera_username: str | None = None,
        camera_password: str | None = None,
        **kwargs,
    ) -> None:
        self.camera_url = camera_url
        self.camera_username = camera_username
        self.camera_password = camera_password
        super().__init__(*args, **kwargs)

    def ctx_camera_request(self, action: str):
        api_path = posixpath.join("api", "v1", "camera", action)
        return self.session.request(
            aiohttp.hdrs.METH_GET,
            urllib.parse.urljoin(self.camera_url, api_path),
            auth=aiohttp.BasicAuth(self.camera_username, self.camera_password),
        )

    async def get_snapshot(self) -> bytes:
        async with self.ctx_camera_request("takeshot") as request:
            return await request.read()

    async def get_state(self) -> APIDataResponse:
        async with self.ctx_camera_request("state") as request:
            return await request.json()

    async def check_auth(self) -> bool:
        async with self.ctx_camera_request("auth_stream") as request:
            return request.status == 501

    @property
    def camera_stream_url(self) -> str:
        parsed_url = urllib.parse.urlparse(self.camera_url)
        return urllib.parse.urlunparse(
            (
                parsed_url.scheme,
                urllib.parse.quote(self.camera_username, safe="")
                + ":"
                + urllib.parse.quote(self.camera_password, safe="")
                + "@"
                + parsed_url.netloc,
                posixpath.join(parsed_url.path, "/api/v1/camera/stream"),
                parsed_url.params,
                "",
                "",
            )
        )


class Raise3DPrinterAPI(Raise3DAPIBase):
    def __init__(
        self, *args, printer_url: str, printer_token: str | None = None, **kwargs
    ) -> None:
        self.printer_url = printer_url
        self.printer_token = printer_token
        super().__init__(*args, **kwargs)

    @staticmethod
    def generate_sign(
        password, timestamp: int | datetime | None = None
    ) -> tuple[str, int]:
        if timestamp is None:
            timestamp = time.time()
        elif isinstance(timestamp, datetime):
            timestamp = timestamp.timestamp()
        if isinstance(timestamp, float):
            timestamp = int(timestamp * 1000)
        else:
            raise ValueError("invalid timestamp argument")

        sha1_hash = hashlib.sha1(
            f"password={password}&timestamp={timestamp}".encode()
        ).hexdigest()
        sign = hashlib.md5(sha1_hash.encode()).hexdigest()
        return sign, timestamp

    # noinspection PyTypeHints
    async def printer_request(
        self,
        method: Literal[aiohttp.hdrs.METH_GET, aiohttp.hdrs.METH_POST],
        endpoint,
        params: dict | None = None,
        json: dict | None = None,
        data=None,
        auth: bool = True,
    ) -> APIDataResponse:
        if self._session.closed:
            raise RuntimeError("Client session is closed!")
        if auth and not self.printer_token:
            raise ValueError("Authentication token is required for this API call.")

        url = f"{self.printer_url}{endpoint}"
        pass_params = {}
        if auth:
            pass_params["token"] = self.printer_token
        if params:
            pass_params.update(params)

        async with self.session.request(
            method, url, json=json, data=data, params=pass_params, raise_for_status=True
        ) as response:
            response_data = await response.json()
            self.logger.debug(f"'{url}' JSON response: {response_data}")
            if response.status == 200 and response_data.get("status") == 1:
                return response_data.get("data")
            try:
                error_code = int(response_data.get("error", {}).get("code"))
            except (TypeError, ValueError):
                raise aiohttp.ClientError(
                    f"API Error: {response_data.get('error', {}).get('msg', 'Unknown error')}"
                )
            error_msg = response_data.get("error", {}).get("msg", "Unknown error")
            raise APIResponseError(
                request_info=response.request_info,
                history=response.history,
                status=error_code,
                message=error_msg,
                headers=response.headers,
            )

    async def _prv1(self, method: str, url: str, *args, **kwargs) -> APIDataResponse:
        return await self.printer_request(method, "/v1" + url, *args, **kwargs)

    async def login(self, sign: str, timestamp: int, **kwargs) -> APIDataResponse:
        return await self._prv1(
            aiohttp.hdrs.METH_GET,
            "/login",
            params={"sign": sign, "timestamp": timestamp},
            auth=False,
            **kwargs,
        )

    # Printer state and statistics
    async def get_system_info(self) -> APIDataResponse:
        return await self._prv1(aiohttp.hdrs.METH_GET, "/printer/system")

    async def get_camera_info(self) -> APIDataResponse:
        return await self._prv1(aiohttp.hdrs.METH_GET, "/printer/camera")

    async def get_running_status(self) -> APIDataResponse:
        return await self._prv1(aiohttp.hdrs.METH_GET, "/printer/runningstatus")

    async def get_basic_info(self) -> APIDataResponse:
        return await self._prv1(aiohttp.hdrs.METH_GET, "/printer/basic")

    async def get_statistics(self) -> APIDataResponse:
        return await self._prv1(aiohttp.hdrs.METH_GET, "/dashboard/statistics")

    # Nozzle control
    async def get_left_nozzle_info(self) -> APIDataResponse:
        return await self._prv1(aiohttp.hdrs.METH_GET, "/printer/nozzle1")

    async def get_right_nozzle_info(self) -> APIDataResponse:
        return await self._prv1(aiohttp.hdrs.METH_GET, "/printer/nozzle2")

    async def set_left_nozzle_temp(self, temperature: int) -> APIDataResponse:
        return await self._prv1(
            aiohttp.hdrs.METH_POST,
            "/printer/nozzle1/temp/set",
            json={"temperature": temperature},
        )

    async def set_right_nozzle_temp(self, temperature: int) -> APIDataResponse:
        return await self._prv1(
            aiohttp.hdrs.METH_POST,
            "/printer/nozzle2/temp/set",
            json={"temperature": temperature},
        )

    async def set_left_nozzle_flowrate(self, flowrate: int) -> APIDataResponse:
        return await self._prv1(
            aiohttp.hdrs.METH_POST,
            "/printer/nozzle1/flowrate/set",
            json={"flowrate": flowrate},
        )

    async def set_right_nozzle_flowrate(self, flowrate: int) -> APIDataResponse:
        return await self._prv1(
            aiohttp.hdrs.METH_POST,
            "/printer/nozzle2/flowrate/set",
            json={"flowrate": flowrate},
        )

    async def set_heatbed_temp(self, temperature: int) -> APIDataResponse:
        return await self._prv1(
            aiohttp.hdrs.METH_POST,
            "/printer/heatbedtemp/set",
            json={"temperature": temperature},
        )

    async def set_feedrate(self, feedrate: int) -> APIDataResponse:
        return await self._prv1(
            aiohttp.hdrs.METH_POST, "/printer/feedrate/set", json={"feedrate": feedrate}
        )

    # Printer control
    async def set_fan_speed(self, fanspeed: int) -> APIDataResponse:
        return await self._prv1(
            aiohttp.hdrs.METH_POST, "/printer/fanspeed/set", json={"fanspeed": fanspeed}
        )

    async def axis_control(
        self,
        is_relative_pos: int | bool,
        x: int | None = None,
        y: int | None = None,
        z: int | None = None,
        e: int | None = None,
        feed: int | None = None,
        nozzle: int | None = None
    ) -> APIDataResponse:
        params = {"is_relative_pos": int(is_relative_pos)}
        if x is not None:
            params["x"] = x
        if y is not None:
            params["y"] = y
        if z is not None:
            params["z"] = z
        if e is not None:
            params["e"] = e
        if nozzle is not None:
            params["nozzle"] = nozzle
        if feed is not None:
            params["feed"] = feed
        return await self._prv1(
            aiohttp.hdrs.METH_POST, "/printer/axiscontrol/set", json=params
        )

    async def move_home(self) -> APIDataResponse:
        return await self.axis_control(False, 0, 0, 0)

    # File positioning operations
    async def move_file(self, file_src: str, file_dst: str) -> APIDataResponse:
        return await self._prv1(
            aiohttp.hdrs.METH_POST,
            "/filepos/moveto",
            data={"file_src": file_src, "file_dst": file_dst},
        )

    async def copy_file(self, file_src: str, file_dst: str) -> APIDataResponse:
        return await self._prv1(
            aiohttp.hdrs.METH_POST,
            "/filepos/copy",
            data={"file_src": file_src, "file_dst": file_dst},
        )

    async def rename_file(self, file_path: str, new_name: str) -> APIDataResponse:
        return await self._prv1(
            aiohttp.hdrs.METH_POST,
            "/filepos/rename",
            data={"file_path": file_path, "new_name": new_name},
        )

    async def delete_file(self, file_path: str) -> APIDataResponse:
        return await self._prv1(
            aiohttp.hdrs.METH_POST, "/filepos/delete", params={"data_path": file_path}
        )

    # Job management operations
    async def get_current_job(self) -> APIDataResponse:
        return await self._prv1(aiohttp.hdrs.METH_GET, "/job/currentjob")

    async def set_current_job(
        self, operate: Literal["pause", "resume", "stop"]
    ) -> APIDataResponse:
        return await self._prv1(
            aiohttp.hdrs.METH_POST, "/job/currentjob", params={"operate": operate}
        )

    async def create_job(self, file_path: str) -> APIDataResponse:
        # @TODO: param may be named 'filepath'
        return await self._prv1(
            aiohttp.hdrs.METH_POST, "/job/create", params={"file_path": file_path}
        )

    async def recover_last_job(self) -> APIDataResponse:
        return await self._prv1(aiohttp.hdrs.METH_POST, "/job/recover/set")

    async def list_jobs(self, start_pos: int = 0, max_num: int = 24) -> APIDataResponse:
        return await self._prv1(
            aiohttp.hdrs.METH_GET,
            "/dashboard/job",
            params={"start_pos": start_pos, "max_num": max_num},
        )

    async def get_job(self, job_id: str, pos: int) -> APIDataResponse:
        return await self._prv1(
            aiohttp.hdrs.METH_GET,
            "/dashboard/job",
            params={"job_id": job_id, "pos": pos},
        )

    async def get_job_image(
        self,
        job_id: str,
        width: int | None = None,
        height: int | None = None,
    ) -> APIDataResponse:
        if height is None:
            height = width or 32
        if width is None:
            width = height
        return await self._prv1(
            aiohttp.hdrs.METH_GET,
            "/dashboard/imagedownload",
            params={"job_id": job_id, "width": width, "height": height},
        )

    # Directory positioning operations
    async def create_directory(self, dir_path: str) -> APIDataResponse:
        return await self._prv1(
            aiohttp.hdrs.METH_POST, "/filepos/dir/create", data={"dir_path": dir_path}
        )

    async def rename_directory(self, dir_path: str, new_name: str) -> APIDataResponse:
        return await self._prv1(
            aiohttp.hdrs.METH_POST,
            "/filepos/dir/rename",
            data={"dir_path": dir_path, "new_name": new_name},
        )

    async def delete_directory(self, dir_path: str) -> APIDataResponse:
        return await self._prv1(
            aiohttp.hdrs.METH_POST, "/filepos/dir/delete", params={"dir_path": dir_path}
        )

    # Content handling operations
    async def upload_file(
        self, file_path: str, destination_path: str
    ) -> APIDataResponse:
        dir_path, _, filename = destination_path.rpartition("/")
        with aiohttp.MultipartWriter("form-data") as mp:
            with open(file_path, "rb") as file:
                # first, desc part
                part = mp.append_json({"dir_path": dir_path})
                part.set_content_disposition("form-data", name="desc")
                # second, file part
                part = mp.append(file)
                part.set_content_disposition(
                    "form-data", name="file", filename=filename
                )
                # send request
                return await self._prv1(
                    aiohttp.hdrs.METH_POST, "/fileops/upload", data=mp
                )

    async def download_image(
        self, data_path: str, width: int | None = None, height: int | None = None
    ) -> APIDataResponse:
        if height is None:
            height = width or 32
        if width is None:
            width = height
        return await self._prv1(
            aiohttp.hdrs.METH_GET,
            "/fileops/imagedownload",
            params={"data_path": data_path, "width": width, "height": height},
        )

    async def list_directory(
        self, directory_path: str = "Local/", start_pos: int = 0, max_num: int = 24
    ) -> APIDataResponse:
        return await self._prv1(
            aiohttp.hdrs.METH_GET,
            "/fileops/list",
            params={"dir": directory_path, "start_pos": start_pos, "max_num": max_num},
        )


class Raise3DStatefulPrinterAPI(Raise3DPrinterAPI):
    def __init__(
        self, *args, printer_password: str, printer_auto_auth: bool = True, **kwargs
    ) -> None:
        self.printer_password = printer_password
        self.printer_auto_auth = printer_auto_auth
        super().__init__(*args, **kwargs)

    async def login(
        self, sign: str | None = None, timestamp: int | None = None, **kwargs
    ) -> APIDataResponse:
        if timestamp is None and sign is not None:
            raise ValueError("signature provided without timestamp")
        sign, timestamp = self.generate_sign(self.printer_password)
        response_data = await super().login(sign, timestamp, auto_auth=False, **kwargs)
        self.printer_token = response_data["token"]
        return response_data

    async def printer_request(
        self, *args, auto_auth: bool | None = None, **kwargs
    ) -> APIDataResponse:
        if auto_auth is None:
            auto_auth = self.printer_auto_auth
        try:
            return await super().printer_request(*args, **kwargs)
        except aiohttp.ClientResponseError as exc:  # @TODO: check authentication
            if not auto_auth or exc.status != 401:
                raise
            self.logger.warning(f"Authentication error upon request: {exc}")
        if self.printer_token:
            self.logger.warning(
                "Authentication lost upon request. Commencing reauthentication..."
            )
        else:
            self.logger.info(
                "Authentication required for following request, performing now..."
            )
        await self.login()
        return await super().printer_request(*args, **kwargs)

    # noinspection PyAttributeOutsideInit
    async def get_camera_info(self) -> APIDataResponse:
        response_data = await super().get_camera_info()
        if isinstance(self, Raise3DCameraAPI):
            self.camera_username = response_data["user_name"]
            self.camera_password = response_data["password"]
            if isinstance(self, Raise3DHostBasedAPIBase):
                self.camera_port = int(
                    response_data["camerserver_URI"].partition("/")[0][1:]
                )
        return response_data


class Raise3DStatefulAPI(Raise3DStatefulPrinterAPI, Raise3DCameraAPI):
    """Aggregation of classes for APIs. URLs still have to be provided manually."""


class Raise3DHostBasedAPIBase(Raise3DAPIBase):
    def __init__(
        self,
        *args,
        host: str | IPv4Address,
        camera_port: int = DEFAULT_CAMERA_PORT,
        printer_port: int = DEFAULT_PRINTER_PORT,
        **kwargs,
    ) -> None:
        assert (
            "printer_url" not in kwargs
        ), "printer_url cannot be provided in host mode"
        assert "camera_url" not in kwargs, "camera_url cannot be provided in host mode"
        if isinstance(host, IPv4Address):
            host = str(host.ip if hasattr(host, "ip") else host)
        self.host = host
        self.camera_port = camera_port
        self.printer_port = printer_port
        super().__init__(
            *args, printer_url=self.printer_url, camera_url=self.camera_url, **kwargs
        )

    @final
    @property
    def camera_port(self) -> int:
        return self._camera_port

    @final
    @camera_port.setter
    def camera_port(self, camera_port: int) -> None:
        self._camera_port = camera_port
        # noinspection HttpUrlsUsage
        self.camera_url = f"http://{self.host}:{self._camera_port}"

    @final
    @property
    def printer_port(self) -> int:
        return self._printer_port

    @final
    @printer_port.setter
    def printer_port(self, printer_port: int) -> None:
        self._printer_port = printer_port
        # noinspection HttpUrlsUsage
        self.printer_url = f"http://{self.host}:{self._printer_port}"


class Raise3DHostBasedStatefulAPI(Raise3DHostBasedAPIBase, Raise3DStatefulAPI):
    """API where only host and printer password is sufficient to operate."""
