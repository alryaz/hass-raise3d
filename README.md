<picture>
  <img alt="Home Assistant + Raise3D" src="https://raw.githubusercontent.com/alryaz/hass-raise3d/main/images/header.png">
</picture>

# Raise3D Integration for Home Assistant

> Use Raise3D local HTTP API to communicate locally, obtain information and perform control operations.  
>
> [![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)  
> [![License](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)  
> [![Supported](https://img.shields.io/badge/Supported%3F-Yes-green.svg?style=for-the-badge)](https://github.com/alryaz/hass-raise3d/graphs/commit-activity)  

> 💵 **Support the project development**  
> [![Donate via YooMoney](https://img.shields.io/badge/YooMoney-8B3FFD.svg?style=for-the-badge)](https://yoomoney.ru/to/410012369233217)  
> [![Donate via Tinkoff](https://img.shields.io/badge/Tinkoff-F8D81C.svg?style=for-the-badge)](https://www.tinkoff.ru/cf/3g8f1RTkf5G)  
> [![Donate via Sberbank](https://img.shields.io/badge/Sberbank-green.svg?style=for-the-badge)](https://www.sberbank.com/ru/person/dl/jc?linkname=3pDgknI7FY3z7tJnN)  
> [![Donate via DonationAlerts](https://img.shields.io/badge/DonationAlerts-fbaf2b.svg?style=for-the-badge)](https://www.donationalerts.com/r/alryaz)  

> 💬 **Technical Support**  
> [![Telegram Group](https://img.shields.io/endpoint?url=https%3A%2F%2Ftg.sumanjay.workers.dev%2Falryaz_ha_addons&style=for-the-badge)](https://telegram.dog/alryaz_ha_addons)

This is not an official integration by Raise3D.

## Installation

### Home Assistant Community Store (HACS)

> 🎉  **Recommended installation method.**

[![Open your Home Assistant and access the repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=alryaz&repository=raise3d&category=integration)

1. Install HACS ([installation guide on the official website](https://hacs.xyz/docs/installation/installation/)).
2. Add the repository to the list of custom repositories:
    1. Open the main page of _HACS_.
    2. Navigate to the _Integrations_ section.
    3. Click the three dots in the top-right corner (additional menu).
    4. Select _Custom Repositories_.
    5. Copy `https://github.com/alryaz/hass-raise3d` into the input field.
    6. Choose _Integration_ from the dropdown menu.
    7. Click _Add_.
3. Search for `Raise3D` in the integrations search _(there may be multiple results!)_.
4. Install the latest version of the component by clicking the `Install` button.
5. Restart the _Home Assistant_ server.

### Manual Installation

> ⚠️ **Warning!** This method is **<ins>not recommended</ins>** due to the difficulty in maintaining the integration up-to-date.

1. Download the [archive with the latest stable version of the integration](https://github.com/alryaz/hass-raise3d/releases/latest/download/raise3d.zip).
2. Create a folder (if it doesn't already exist) named `custom_components` inside your Home Assistant configuration directory.
3. Create a folder named `raise3d` inside the `custom_components` folder.
4. Extract the contents of the downloaded archive into the `raise3d` folder.
5. Restart the _Home Assistant_ server.

## Printer Connection Setup

To enable data exchange between Home Assistant and the printer, configure the integration with the following parameters:

- **Hostname or IP Address**: Enter the printer's IP address or hostname within your local network.
- **Port**: Default is **10800** (camera communication is done over a different port).
- **Printer Password**: Enter the [**Access password**](#step-no-3-set-access-password) used for API communication _(see manual below on how to set it up)_.
- **Polling Frequency**: Defines how often data is polled from the device (default is **30 seconds**).


## Enabling Raise3D API on your printer

Raise3D provides an API that allows interfacing with the printer via HTTP using JSON (primarily).  It is deactivated by default (isolated for cloud purposes).

The following steps are mandatory to get this component working.

### Step no. 1: Secure Password

1. Navigate to **Machine > More Settings > Privacy and Security**.
2. Tap on **Secure Settings**.
3. Enable **Secure Settings and Secure password**.
4. A window will appear; tap the eye icon to view the secure password. Note this password.

### Step no. 2: Enable API

1. Navigate to **Machine** > **Developer**.
2. Tap on **Enable Remote Access API** (if not already enabled).
3. Enter the secure password from the previous step.
4. Upon successful verification, a message will confirm that the API is enabled.

### Step no. 3: Set access password

1. Navigate to **Machine > Developer > Access password**.
2. Tap the eye icon to view the access password. Note this password.