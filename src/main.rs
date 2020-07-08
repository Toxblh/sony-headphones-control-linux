use std::str::FromStr;
use clap::{App};
use bluetooth_serial_port::{BtSocket, BtProtocol, BtAddr};
use std::io::Write;

/**
 * enabled: bool;
 * noiseCancelling: 0, 1, 2;
 * volume: 0-19;
 * voice: 0, 1;
 */
fn get_packet(enabled: bool, noise_cancelling: u8, volume: u8, voice: u8) -> [u8;17]  {
    let mut enabled_value = 16;

    if !enabled {
        enabled_value = 0;
    }

    let data:[u8;14] = [12, 0, 0, 0, 0, 8, 104, 2, enabled_value, 2, noise_cancelling, 1, voice, volume];

    let control_sum: u8 = data.iter().fold(0, |sum, elem| sum + elem);

    let mut ready_packet:Vec<u8> =  Vec::new();
    ready_packet.push(62);
    ready_packet.extend_from_slice(&data);
    ready_packet.push(control_sum);
    ready_packet.push(60);

    let mut output:[u8;17] = [0;17];
    output.copy_from_slice(ready_packet.into_iter().as_slice());
    output
}

fn main() {
    //
    //
    // Arguments of application
    //
    //

    let matches = App::new("sony-headphones-linux")
        .version("1.0")
        .author("Anton Palgunov <toxblh@gmail.com>")
        .about("Switch modes of Sony WH/WI headphones")
        .arg("<MAC> 'Set a mac address bluetooth headphones'")
        .arg("<MODE> 'Set one of mode headphones: noise-cancelling, wind-cancelling,  ambient-sound, disable'")
        .get_matches();

    let mac = matches.value_of("MAC").unwrap();
    let mode = matches.value_of("MODE").unwrap();

    println!("MAC: {}", mac);
    println!("MODE: {}", mode);

    //
    //
    // Ready packet
    //
    //

    let ambient_sound_bytes;
    if mode == "noise-cancelling" {
        ambient_sound_bytes = get_packet(true, 2, 0, 0);
    }

    else if mode == "wind-cancelling" {
        ambient_sound_bytes = get_packet(true, 1, 0, 0);
    }

    else if mode == "ambient-sound" {
        ambient_sound_bytes = get_packet(true, 0, 19, 0);
    }

    else if mode == "disable" {
        ambient_sound_bytes = get_packet(false, 0, 0, 0);
    }

    else {
        println!("Unknown mode, exiting");
        std::process::exit(1);
    }

    println!("Bytes {:?}", ambient_sound_bytes);

    //
    //
    // Bluetooth part
    //
    //

    let _uuid_mode = std::string::String::from("96cc203e-5068-46ad-b32d-e316f5e069ba");

    let mut socket = BtSocket::new(BtProtocol::RFCOMM).unwrap();
    let addr = BtAddr::from_str(&mac).unwrap();

    // TODO: Manual write connection to RFCOMM socket via grab info from about port from service

    match socket.connect(addr) {
        Ok(())  => (),
        Err(e) => {
            println!("Error: {}", e);
            std::process::exit(1);
        },
    };

    let num_bytes_written = socket.write(&ambient_sound_bytes).unwrap();
    println!("Wrote `{}` bytes", num_bytes_written);
}
