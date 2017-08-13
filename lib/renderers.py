import math


class RendererConfig:
    def __init__(self, renderer, measure, name, x_start=0, x_step=1):
        self.renderer = renderer
        self.measure = measure
        self.name = name
        self.x_start = x_start
        self.x_step = x_step


class Renderer:
    def __init__(self):
        pass

    def render(self, draw, config, data):
        raise NotImplementedError


class BarRenderer(Renderer):
    def __init__(self):
        Renderer.__init__(self)

    def render(self, draw, config, data, data_function=None, header_function=None, count_function=None,
               render_max=True):
        if header_function is not None:
            header = header_function(config, data)
        else:
            header = config.name

        draw.text((1, 0), header, fill="white")
        draw.line([(0, 11), (128, 11)], fill="white", width=1)
        draw.line([(2, 63), (126, 63)], fill="white", width=1)

        if count_function is None:
            max_count = float(max(max(data[config.measure]), 100))
        else:
            max_count = count_function(config, data)

        if data_function is not None:
            measures = data_function(config, data)
        else:
            measures = data[config.measure]

        x = config.x_start
        for i, measure in reversed(list(enumerate(measures))):
            height = math.ceil(50 * (measure / max_count))
            draw.rectangle([(x, 63), (x - 2, 63 - height)], fill="white", outline=None)
            x = x + config.x_step

        if render_max:
            count = '%g' % max_count
            draw.rectangle([(1, 12), (6 * len(count), 22)], fill="black", outline="black")
            draw.text((1, 13), count, fill="white")


class LabeledBarRenderer(Renderer):
    def render(self, draw, config, data, data_function=None, header_function=None, count_function=None,
               keys_function=None, render_max=True, bar_width=6):
        if header_function is not None:
            header = header_function(config, data)
        else:
            header = config.name

        draw.text((1, 0), header, fill="white")
        draw.line([(0, 11), (128, 11)], fill="white", width=1)
        draw.line([(0, 63 - 10), (128, 63 - 10)], fill="white", width=1)

        if count_function is not None:
            max_count = count_function(config, data)
        else:
            max_count = 100

        if keys_function is not None:
            keys = keys_function(config, data)
        else:
            keys = data[config.measure].keys()

        if data_function is not None:
            measures = data_function(config, data)
        else:
            measures = data[config.measure]

        x = config.x_start
        for key in keys:
            value = measures[key]
            width = bar_width / 2
            height = math.ceil(42 * (sum(value) / max_count))
            midpoint = x - 1 + (6 * len(key)) / 2
            draw.text((x, 63 - 10), key, fill="white")
            draw.rectangle([(midpoint - width, 63 - 10), (midpoint + width, 63 - 10 - height)], fill="white",
                           outline=None)
            x = x + config.x_step

        if render_max:
            count = '%g' % max_count
            draw.rectangle([(1, 12), (6 * len(count), 22)], fill="black", outline="black")
            draw.text((1, 13), count, fill="white")


class UpDownRenderer(Renderer):
    def __init__(self):
        Renderer.__init__(self)

    def render(self, draw, config, data, render_max=True, count_function=None, header_function=None, up_mesasure='in',
               down_measure='out', min_value=1024):
        if header_function is not None:
            header = header_function(config, data)
        else:
            header = config.name

        draw.text((1, 0), "%s" % header, fill="white")
        draw.line([(0, 11), (128, 11)], fill="white", width=1)
        draw.line([(2, 38), (126, 38)], fill="white", width=1)

        if count_function is not None:
            max_count = count_function(config, data)
        else:
            max_count = float(max(max(data[config.measure][up_mesasure]), max(data[config.measure][down_measure]),
                                  min_value))

        x = config.x_start
        for i, measure in reversed(list(enumerate(data[config.measure][up_mesasure]))):
            up_height = math.ceil(25 * float(measure / max_count))
            draw.rectangle([(x, 38), (x - 2, 38 - up_height)], fill="white", outline=None)

            x = x + config.x_step

        x = config.x_start
        for i, measure in reversed(list(enumerate(data[config.measure][down_measure]))):
            down_height = math.ceil(25 * float(measure / max_count))
            draw.rectangle([(x, 38), (x - 2, 38 + down_height)], fill="white", outline=None)

            x = x + config.x_step

        if render_max:
            draw.rectangle([(1, 12), (6 * len(config.name), 22)], fill="black", outline="black")
            draw.text((1, 13), config.name, fill="white")


class QuadCpuRenderer(Renderer):
    def __init__(self):
        Renderer.__init__(self)

    def render(self, draw, config, data):
        vertexes = [(0, 31), (65, 31), (0, 63), (65, 63)]

        for i, vertex in enumerate(vertexes):
            draw.line([(vertex[0] + 1, vertex[1]), (vertex[0] + 62, vertex[1])], fill="white", width=1)

            x = vertex[0] + 62
            for measure in reversed(list(data[config.measure][i])):
                height = math.ceil(30 * measure / 100)
                draw.line([(x, vertex[1]), (x, vertex[1] - height)], fill="white", width=1)
                x = x - 1

            text = '%.2f%%' % data[config.measure][i][-1]
            draw.rectangle([(vertex[0], vertex[1] - 31), (vertex[0] + (6 * len(text)), vertex[1] - 31 + 10)],
                           fill="black", outline="black")
            draw.text((vertex[0] + 1, vertex[1] - 31), text, fill="white")
