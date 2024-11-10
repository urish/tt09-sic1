# Bringup script for the SIC1 computer - runs the 7-segment counter program.

from machine import Pin
import time


def set_pc(tt, addr: int):
    tt.input_byte = addr
    tt.uio2.high()  # set_pc
    tt.clock_project_once()
    tt.uio2.low()


def load_program(tt, addr: int, program: List[int]):
    set_pc(tt, addr)
    for byte in program:
        tt.input_byte = byte
        tt.uio3.high()  # load_data
        tt.clock_project_once()
        tt.uio3.low()
    tt.input_byte = 0


def run():
    tt = DemoBoard.get()
    tt.shuttle.tt_um_urish_sic1.enable()
    tt.clock_project_stop()
    tt.mode = RPMode.ASIC_RP_CONTROL
    tt.input_byte = 0
    tt.bidir_mode = [Pin.IN] * 8
    tt.bidir_byte = 0
    tt.uio0.mode = Pin.OUT  # run
    tt.uio2.mode = Pin.OUT  # set_pc
    tt.uio3.mode = Pin.OUT  # load_data

    # Reset the project
    tt.reset_project(True)
    for _ in range(10):
        tt.clock_project_once()
    tt.reset_project(False)
    for _ in range(10):
        tt.clock_project_once()

    # fmt: off
    # Source: programs/count_7segment.sic1
    load_program(tt, 0, [
        0x2d, 0x42, 0x03, 0x2e, 0x2e, 0x06, 0x2e, 0x2d, 0x09, 0x2d, 0x2d, 0x0c, 0x2d, 0x2e, 0x0f, 0x22,
        0x22, 0x12, 0x22, 0x2d, 0x15, 0x1e, 0x1e, 0x18, 0x1e, 0x2d, 0x1b, 0x2d, 0x2d, 0x1e, 0x2d, 0x2f,
        0x00, 0x2d, 0x00, 0x24, 0xfe, 0x2d, 0x27, 0x2e, 0x30, 0x2a, 0x2d, 0x2d, 0x0c, 0x00, 0x00, 0x00,
        0xff, 0x3f, 0x06, 0x5b, 0x4f, 0x66, 0x6d, 0x7d, 0x07, 0x7f, 0x6f, 0x77, 0x7c, 0x39, 0x5e, 0x79,
        0x71, 0x00, 0x31, 0x00,
    ])
    # fmt: on
    set_pc(tt, 0)
    tt.uio0.high()  # run
    tt.clock_project_once()

    while tt.uio1.value() == 0:  # not halted
        time.sleep(0.01)  # ~10ms / 100Hz
        tt.clock_project_once()
        print(".", end="")


run()
