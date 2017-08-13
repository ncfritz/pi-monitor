import psutil
import time

from collections import deque

from exceptions import NotImplementedError
from exceptions import EnvironmentError

from luma.core.render import canvas

from renderers import BarRenderer
from renderers import QuadCpuRenderer
from renderers import RendererConfig
from renderers import UpDownRenderer
from utils import bytes_to_human


class Screen:

    def __init__(self):
        pass

    def render(self, display):
        raise NotImplementedError()

    def collect(self):
        raise NotImplementedError()

    def next_screen(self):
        pass

    def previous_screen(self):
        pass

    def reset_screen(self):
        pass

    def sleep_interval(self):
        return 1


class CpuScreen(Screen):

    def __init__(self):
        Screen.__init__(self)

        self.measures = {
            'cores': [
                deque(maxlen=62),
                deque(maxlen=62),
                deque(maxlen=62),
                deque(maxlen=62)
            ],
            'percent': deque(maxlen=31),
            'user': {
                'values': deque(maxlen=31), 'last': None
            },
            'system': {
                'values': deque(maxlen=31), 'last': None
            },
            'idle': {
                'values': deque(maxlen=31), 'last': None
            },
            'nice': {
                'values': deque(maxlen=31), 'last': None
            },
            'iowait': {
                'values': deque(maxlen=31), 'last': None
            },
            'irq': {
                'values': deque(maxlen=31), 'last': None
            },
            'softirq': {
                'values': deque(maxlen=31), 'last': None
            },
            'steal': {
                'values': deque(maxlen=31), 'last': None
            },
            'guest': {
                'values': deque(maxlen=31), 'last': None
            },
            'guest_nice': {
                'values': deque(maxlen=31), 'last': None
            }
        }
        self.screen_config = [
            RendererConfig(QuadCpuRenderer(), 'cores', 'CPU'),
            RendererConfig(BarRenderer(), 'percent', 'CPU', x_start=126, x_step=-4),
            RendererConfig(BarRenderer(), 'user', 'User', x_start=126, x_step=-4),
            RendererConfig(BarRenderer(), 'system', 'System', x_start=126, x_step=-4),
            RendererConfig(BarRenderer(), 'idle', 'Idle', x_start=126, x_step=-4),
            RendererConfig(BarRenderer(), 'nice', 'Nice', x_start=126, x_step=-4),
            RendererConfig(BarRenderer(), 'iowait', 'IOWait', x_start=126, x_step=-4),
            RendererConfig(BarRenderer(), 'irq', 'IRQ', x_start=126, x_step=-4),
            RendererConfig(BarRenderer(), 'softirq', 'Soft IRQ', x_start=126, x_step=-4),
            RendererConfig(BarRenderer(), 'steal', 'Steal',  x_start=126, x_step=-4),
            RendererConfig(BarRenderer(), 'guest', 'Guest', x_start=126, x_step=-4),
            RendererConfig(BarRenderer(), 'guest_nice', 'Guest Nice', x_start=126, x_step=-4)
        ]
        self.screen_index = 0

    def next_screen(self):
        self.screen_index = self.screen_index + 1 if self.screen_index + 1 < len(self.screen_config) else 0

    def previous_screen(self):
        self.screen_index = self.screen_index - 1 if self.screen_index - 1 >= 0 else len(self.screen_config) - 1

    def reset_screen(self):
        self.screen_index = 0

    def get_header(self, config, data):
        return '%s:%.2f' % (config.name, data[config.measure]['values'][-1])

    def get_cpu_header(self, config, data):
        return '%s:%s%%' % (config.name, data[config.measure][-1])

    def get_data_values(self, config, data):
        return data[config.measure]['values']

    def count_values(self, config, data):
        return float(max(max(data[config.measure]['values']), 100))

    def render(self, display):

        with canvas(display) as draw:
            config = self.screen_config[self.screen_index]

            if self.screen_index == 0:
                config.renderer.render(draw,
                                       config,
                                       self.measures)
            elif self.screen_index == 1:
                config.renderer.render(draw,
                                       config,
                                       self.measures,
                                       header_function=self.get_cpu_header,
                                       render_max=False)
            elif self.screen_index in (2, 3, 4, 5, 6, 7, 8, 9, 10, 11):
                config.renderer.render(draw,
                                       config,
                                       self.measures,
                                       header_function=self.get_header,
                                       data_function=self.get_data_values,
                                       render_max=False,
                                       count_function=self.count_values)

    def collect_init(self, name, measure):
        self.measures[name]['last'] = measure

    def collect_record(self, name, measure):
        last = self.measures[name]['last']

        self.measures[name]['values'].append(measure - last)
        self.measures[name]['last'] = measure

    def collect(self):

        usage = psutil.cpu_times(percpu=False)

        self.collect_init('user', usage.user)
        self.collect_init('system', usage.system)
        self.collect_init('idle', usage.idle)
        self.collect_init('nice', usage.nice)
        self.collect_init('iowait', usage.iowait)
        self.collect_init('irq', usage.irq)
        self.collect_init('softirq', usage.softirq)
        self.collect_init('steal', usage.steal)
        self.collect_init('guest', usage.guest)
        self.collect_init('guest_nice', usage.guest_nice)

        while True:
            # Record the CPU percent
            self.measures['percent'].append(psutil.cpu_percent(interval=None))

            # Record the CPU times
            usage = psutil.cpu_times(percpu=False)

            self.collect_record('user', usage.user)
            self.collect_record('system', usage.system)
            self.collect_record('idle', usage.idle)
            self.collect_record('nice', usage.nice)
            self.collect_record('iowait', usage.iowait)
            self.collect_record('irq', usage.irq)
            self.collect_record('softirq', usage.softirq)
            self.collect_record('steal', usage.steal)
            self.collect_record('guest', usage.guest)
            self.collect_record('guest_nice', usage.guest_nice)

            # And the per-core measures
            cpu_measures = psutil.cpu_percent(interval=None, percpu=True)

            for i, measure in enumerate(cpu_measures):
                self.measures['cores'][i].append(measure)

            time.sleep(1)


class NetworkScreen(Screen):
    def __init__(self, interface):
        Screen.__init__(self)

        self.interface = interface
        self.ip = None
        self.measures = {
            'bytes': {
                'in': deque(maxlen=31), 'out': deque(maxlen=31), 'last_in': None, 'last_out': None
            },
            'packets': {
                'in': deque(maxlen=31), 'out': deque(maxlen=31), 'last_in': None, 'last_out': None
            },
            'errors': {
                'in': deque(maxlen=31), 'out': deque(maxlen=31), 'last_in': None, 'last_out': None
            },
            'dropped': {
                'in': deque(maxlen=31), 'out': deque(maxlen=31), 'last_in': None, 'last_out': None
            }
        }
        self.screen_config = [
            RendererConfig(UpDownRenderer(), 'bytes', 'Bytes', x_start=126, x_step=-4),
            RendererConfig(UpDownRenderer(), 'packets', 'Packets', x_start=126, x_step=-4),
            RendererConfig(UpDownRenderer(), 'errors', 'Errors', x_start=126, x_step=-4),
            RendererConfig(UpDownRenderer(), 'dropped', 'Dropped', x_start=126, x_step=-4)
        ]
        self.screen_index = 0

        interfaces = psutil.net_if_addrs()[self.interface]

        for interface in interfaces:

            if interface.family == 2:
                self.ip = interface.address
                break

        if self.ip is None:
            raise EnvironmentError()

    def next_screen(self):
        self.screen_index = self.screen_index + 1 if self.screen_index + 1 < len(self.screen_config) else 0

    def previous_screen(self):
        self.screen_index = self.screen_index - 1 if self.screen_index - 1 >= 0 else len(self.screen_config) - 1

    def reset_screen(self):
        self.screen_index = 0

    def get_header(self, config, data):
        return "%s:%s" % (self.interface, self.ip)

    def render(self, display):
        with canvas(display) as draw:
            config = self.screen_config[self.screen_index]
            config.renderer.render(draw,
                                   config,
                                   self.measures,
                                   header_function=self.get_header,
                                   min_value=10240)

    def collect_init(self, name, in_measure, out_measure):
        self.measures[name]['last_in'] = in_measure
        self.measures[name]['last_out'] = out_measure

    def collect_record(self, name, in_measure, out_measure):
        last_in = self.measures[name]['last_in']
        last_out = self.measures[name]['last_out']

        self.measures[name]['in'].append(in_measure - last_in)
        self.measures[name]['out'].append(out_measure - last_out)

        self.measures[name]['last_in'] = in_measure
        self.measures[name]['last_out'] = out_measure

    def collect(self):

        usage = psutil.net_io_counters(pernic=True)

        self.collect_init('bytes', usage[self.interface].bytes_recv, usage[self.interface].bytes_sent)
        self.collect_init('packets', usage[self.interface].packets_recv, usage[self.interface].packets_sent)
        self.collect_init('errors', usage[self.interface].errout, usage[self.interface].errin)
        self.collect_init('dropped', usage[self.interface].dropout, usage[self.interface].dropin)

        while True:
            usage = psutil.net_io_counters(pernic=True)

            self.collect_record('bytes', usage[self.interface].bytes_recv, usage[self.interface].bytes_sent)
            self.collect_record('packets', usage[self.interface].packets_recv, usage[self.interface].packets_sent)
            self.collect_record('errors', usage[self.interface].errout, usage[self.interface].errin)
            self.collect_record('dropped', usage[self.interface].dropout, usage[self.interface].dropin)

            time.sleep(1)


class MemoryScreen(Screen):
    def __init__(self):
        Screen.__init__(self)

        self.used = 0
        self.total = 0
        self.measures = {
            'percent': deque(maxlen=31),
            'used': deque(maxlen=31),
            'available': deque(maxlen=31),
            'free': deque(maxlen=31),
            'active': deque(maxlen=31),
            'inactive': deque(maxlen=31),
            'buffers': deque(maxlen=31),
            'cached': deque(maxlen=31),
            'shared': deque(maxlen=31)
        }
        self.screen_config = [
            RendererConfig(BarRenderer(), 'percent', 'Percent', x_start=126, x_step=-4),
            RendererConfig(BarRenderer(), 'used', 'Used', x_start=126, x_step=-4),
            RendererConfig(BarRenderer(), 'available', 'Available', x_start=126, x_step=-4),
            RendererConfig(BarRenderer(), 'free', 'Free', x_start=126, x_step=-4),
            RendererConfig(BarRenderer(), 'active', 'Active', x_start=126, x_step=-4),
            RendererConfig(BarRenderer(), 'inactive', 'Inactive', x_start=126, x_step=-4),
            RendererConfig(BarRenderer(), 'buffers', 'Buffers', x_start=126, x_step=-4),
            RendererConfig(BarRenderer(), 'cached', 'Cached', x_start=126, x_step=-4),
            RendererConfig(BarRenderer(), 'shared', 'Shared', x_start=126, x_step=-4),
        ]
        self.screen_index = 0

    def next_screen(self):
        self.screen_index = self.screen_index + 1 if self.screen_index + 1 < len(self.screen_config) else 0

    def previous_screen(self):
        self.screen_index = self.screen_index - 1 if self.screen_index - 1 >= 0 else len(self.screen_config) - 1

    def reset_screen(self):
        self.screen_index = 0

    def get_pct_header(self, config, data):
        return "Memory:%s%%" % data[config.measure][-1]

    def get_mem_header(self, config, data):
        return "%s:%s/%s" % (config.name, bytes_to_human(data[config.measure][-1]), bytes_to_human(self.total))

    def get_max_mem(self, config, data):
        return self.total + 0.0

    def render(self, display):
        with canvas(display) as draw:
            config = self.screen_config[self.screen_index]

            if self.screen_index == 0:
                config.renderer.render(draw,
                                       config,
                                       self.measures,
                                       header_function=self.get_pct_header,
                                       render_max=False)
            elif self.screen_index in (1, 2, 3, 4, 5, 6, 7, 8):
                config.renderer.render(draw,
                                       config,
                                       self.measures,
                                       header_function=self.get_mem_header,
                                       count_function=self.get_max_mem,
                                       render_max=False)

    def collect(self):

        while True:
            usage = psutil.virtual_memory()

            self.used = usage.used
            self.total = usage.total

            self.measures['percent'].append(usage.percent)
            self.measures['used'].append(usage.used)
            self.measures['available'].append(usage.available)
            self.measures['free'].append(usage.free)
            self.measures['active'].append(usage.active)
            self.measures['inactive'].append(usage.inactive)
            self.measures['buffers'].append(usage.buffers)
            self.measures['cached'].append(usage.cached)
            self.measures['shared'].append(usage.shared)

            time.sleep(1)
