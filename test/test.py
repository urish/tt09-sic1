# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge
from typing import List

ADDR_IN = 253
ADDR_OUT = 254
ADDR_HALT = 255

UIO_RUN = 1 << 0
UIO_SET_PC = 1 << 2
UIO_LOAD_DATA = 1 << 3


class OutputMonitor:
    def __init__(self, dut):
        self.dut = dut
        self.queue = []
        self._monitor = cocotb.fork(self._run())

    async def _run(self):
        while True:
            await RisingEdge(self.dut.out_strobe)
            if self.dut.uo_out.value.integer != 0:
                self.queue.append(self.dut.uo_out.value.integer)

    def get(self):
        return self.queue

    def get_string(self):
        return "".join([chr(c) for c in self.queue])

    def clear(self):
        self.queue = []


class SIC1Driver:
    def __init__(self, dut):
        self.dut = dut

        # Set the clock period to 10 us (100 KHz)
        self.clock = Clock(dut.clk, 10, units="us")
        cocotb.start_soon(self.clock.start())

        self.output = OutputMonitor(dut)

    async def reset(self):
        self.dut._log.info("Reset")
        self.dut.ena.value = 1
        self.dut.ui_in.value = 0
        self.dut.uio_in.value = 0
        self.dut.rst_n.value = 0
        await ClockCycles(self.dut.clk, 10)
        self.dut.rst_n.value = 1
        await ClockCycles(self.dut.clk, 10)

    async def set_pc(self, addr: int):
        self.dut.uio_in.value = UIO_SET_PC
        self.dut.ui_in.value = addr
        await ClockCycles(self.dut.clk, 1)
        self.dut.uio_in.value = 0

    async def write_mem(self, addr: int, data: int):
        await self.set_pc(addr)
        self.dut.uio_in.value = UIO_LOAD_DATA
        self.dut.ui_in.value = data
        await ClockCycles(self.dut.clk, 1)
        self.dut.uio_in.value = 0

    async def write_mem_bytes(self, addr: int, data: List[int]):
        await self.set_pc(addr)
        for d in data:
            self.dut.uio_in.value = UIO_LOAD_DATA
            self.dut.ui_in.value = d
            await ClockCycles(self.dut.clk, 1)
            self.dut.uio_in.value = 0

    async def step(self, n: int = 1):
        for _ in range(n):
            self.dut.uio_in.value = UIO_RUN
            await ClockCycles(self.dut.clk, 1)
            self.dut.uio_in.value = 0
            await ClockCycles(self.dut.clk, 6)  # Each instruction takes 6 clock cycles
        # An extra clock cycle for outputs to stablize:
        await ClockCycles(self.dut.clk, 1)

    async def run(self):
        self.dut.uio_in.value = UIO_RUN
        await ClockCycles(self.dut.clk, 1)
        await RisingEdge(self.dut.halted)
        self.dut.uio_in.value = 0
        # An extra clock cycle for outputs to stablize:
        await ClockCycles(self.dut.clk, 1)


@cocotb.test()
async def test_basic_io(dut):
    sic1 = SIC1Driver(dut)
    await sic1.reset()

    await sic1.write_mem(0x00, ADDR_OUT)
    await sic1.write_mem(0x01, ADDR_IN)
    await sic1.write_mem(0x02, 0x10)
    await sic1.set_pc(0x00)

    dut.ui_in.value = 15
    await sic1.step()
    assert dut.uo_out.value.signed_integer == -15


@cocotb.test()
async def test_branching(dut):
    sic1 = SIC1Driver(dut)
    await sic1.reset()

    # fmt: off
    await sic1.write_mem_bytes(0x0, [
        0x00, 0x00, 0x06,  # PC <- 6
        0xfe, 0x00, 0x00,  # OUT <- 0xff, PC <- 0
        0xfe, 0x09, 0x00,  # OUT <- 0x1
        0xff, 0xff, 0xff  # data for previous instruction + HALT
    ])
    # fmt: on

    await sic1.set_pc(0x00)
    await sic1.run()

    assert dut.uo_out.value.signed_integer == 0x01


@cocotb.test()
async def test_print_tinytapeout(dut):
    sic1 = SIC1Driver(dut)
    await sic1.reset()

    # fmt: off
    # Source: programs/print_hello_tinytapeout.sic1
    await sic1.write_mem_bytes(0x0, [
        0x21, 0x22, 0x03, 0x16, 0x16, 0x06, 0x16, 0x21, 0x09, 0x12, 0x12, 0x0c, 0x12, 0x21, 0x0f, 0x21, 
        0x21, 0x12, 0x21, 0x23, 0xff, 0x21, 0x00, 0x18, 0xfe, 0x21, 0x1b, 0x22, 0x24, 0x1e, 0x21, 0x21,
        0x00, 0x00, 0x25, 0x00, 0xff, 0x48, 0x65, 0x6c, 0x6c, 0x6f, 0x2c, 0x20, 0x54, 0x69, 0x6e, 0x79,
        0x20, 0x54, 0x61, 0x70, 0x65, 0x6f, 0x75, 0x74, 0x21, 0x00
    ])
    # fmt: on

    await sic1.set_pc(0x00)
    await sic1.run()

    dut._log.info(f"Program output: {sic1.output.get_string()}")
    assert sic1.output.get_string() == "Hello, Tiny Tapeout!"
