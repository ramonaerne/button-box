# Modification

This document suggets to an AI what needs to be done in the fork of this repo to make my alternative hardware set-up work. The goal is to use as much of the button-box code and tooling as possible and to develop alternative tools and PRs / features to bridge the gaps to achieve the goal of the modified product.

## Goal

The goal is a similar looking button-box as suggested in the github repo. A device (inside of a box) that can be plugged in via some kind of AC wall-plug that will automatically sign in to a WIFI network (or allow provisioning to make that happen), a way to connect to a messaging app (tbd) such that: There will be two connected "channels" and each channel is handled on a custom button each. There will initially be two buttons, so two channels available. Each channel is a way to communicate via voice messages to a single account on that messaging app and be fixed, although reassignable somehow.

The button press logic we can reuse if possible from the button box, to listen to incoming voice message and somehow via another press (e.g. long press) be able to record a new message. There should be somehow a way to limit the number of messages receivable and sendable per day to not confuse things too much.


## Hardware

The hardware used will be a raspberrypi zero 2 and with a microusb to audio dongle that will connect on the aux input a microphone, and on the aux output small usb speakers. The software should make sure that the microphone is not in listening mode at all time but only when the button press activates it. There will be two arcade buttons hooked up both as button to gpios as well as with the LED via a external MOSFET, such that the LED can be activated via gpio but the power is supplied via the 5v power rail. 

## Messaging

The goal is to use signal messenger also eventually but initially whatsapp is just fine.