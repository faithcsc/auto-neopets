# Auto Neopets

Automated tasks on Neopets for multiple accounts within a Docker container while connecting to Neopets through NordVPN.

Supported tasks:

- Trudy's surprise
- Collect bank interest
- Auto upgrade bank account to highest available interest rate
- Deposit all NP on hand into bank

# Requirements

- Ubuntu 18.04+
- Docker
- Internet connection
- NordVPN paid account

# Quick start

1. Compile Docker image

`cd container && ./rebuild-images`

2. Place account passwords in `conf/secret-neopets` and NordVPN username and password in `conf/secret-vpn` in this format:

`conf/secret-neopets`:
```
{
    "username_1": {
        "username": "username_1",
        "password": "password_1",
        "city": "Amsterdam", # NordVPN city that is associated with this acc
    },
    "username_2": {
        ...
    },
    ...
}
```

`conf/secret-vpn`:
```
VPN_USERNAME="bobby@gmail.com"
VPN_PASSWORD=somePasswordHerePreferablyAlphanumericNoSpecialCharacters29
```

3. Run the Docker image using

```
cd scripts ; ./start
```

Logs are stored in `logs/`.
