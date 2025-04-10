# RetroSpin for MiSTer

> **WARNING**: This repository is in active development. There are no guarantees about stability. 

## Overview

This project launches games on MiSTer by reading a game_id directly from a game disc and launching that game if it exists. If the game is not located locally, it will prompt you to install it. Game names are checked against the [redump.org](http://redump.org/) database for saving and for launching.

## Status of Features

#### Systems Supported
- [x] Sony Playstation
- [x] Sega Saturn
- [ ] Sega Mega CD & Sega CD
- [ ] Sega 32X
- [ ] Neo Geo CD
- [ ] NEC PC Engine CD & TurboGrafx CD
- [ ] Philips CD-i
- [ ] Panasonic 3DO Interactive Multiplayer

#### Features
- [ ] Can be installed by running update_all command (Need to create db file)
- [x] Save disc and .bin + .cue to correct game folder. Game will only be saved to USB drive.
- [ ] Option to save disc as .chd
- [ ] Add support to save to SD card

