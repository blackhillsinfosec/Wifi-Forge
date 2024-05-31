"""
    Mininet-WiFi: A simple networking testbed for Wireless OpenFlow/SDWN!
    author: Ramon Fontes (ramonrf@dca.fee.unicamp.br)
"""

import warnings
import numpy as np
import matplotlib.patches as patches
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mininet.log import debug


class Plot3D (object):
    ax = None

    def __init__(self, **kwargs):
        self.instantiate_graph(**kwargs)

    def instantiate_graph(self, min_x, min_y, min_z, max_x, max_y, max_z,
                          **kwargs):
        plt.ion()
        plt.figure(1)
        plt.title("Mininet-WiFi Graph")
        Plot3D.ax = plt.subplot(111, projection=Axes3D.name)
        self.ax.set_xlabel('meters (x)')
        self.ax.set_ylabel('meters (y)')
        self.ax.set_zlabel('meters (z)')
        self.ax.set_xlim([min_x, max_x])
        self.ax.set_ylim([min_y, max_y])
        self.ax.set_zlim([min_z, max_z])
        self.ax.grid(True)
        self.instantiate_nodes(**kwargs)

    def instantiate_nodes(self, nodes, **kwargs):
        for node in nodes:
            self.instantiate_attrs(node)
            self.draw()

    @classmethod
    def instantiate_attrs(cls, node):
        cls.instantiate_annotate(node)
        cls.instantiate_node(node)
        cls.instantiate_circle(node)

    @classmethod
    def instantiate_annotate(cls, node):
        x, y, z = node.getxyz()
        node.plttxt = Plot3D.ax.text(x, y, z, node.name)

    @classmethod
    def instantiate_node(cls, node):
        x, y, z = node.getxyz()
        resolution = 40
        u = np.linspace(0, 2 * np.pi, resolution)
        v = np.linspace(0, np.pi, resolution)

        r = 1
        x = r * np.outer(np.cos(u), np.sin(v)) + x
        y = r * np.outer(np.sin(u), np.sin(v)) + y
        z = r * np.outer(np.ones(np.size(u)), np.cos(v)) + z

        node.plt_node = Plot3D.ax.plot_surface(x, y, z, alpha=0.2,
                                               edgecolor='none',
                                               color='black')

    @classmethod
    def instantiate_circle(cls, node):
        x, y, z = node.getxyz()
        color = node.get_circle_color()

        resolution = 100
        u = np.linspace(0, 2 * np.pi, resolution)
        v = np.linspace(0, np.pi, resolution)

        r = cls.get_max_radius(node)
        x = r * np.outer(np.cos(u), np.sin(v)) + x
        y = r * np.outer(np.sin(u), np.sin(v)) + y
        z = r * np.outer(np.ones(np.size(u)), np.cos(v)) + z

        node.circle = Plot3D.ax.plot_surface(x, y, z, alpha=0.2,
                                             edgecolor='none',
                                             color=color)

    @classmethod
    def get_max_radius(cls, node):
        range_list = []
        for n in node.wintfs.values():
            range_list.append(n.range)
        return max(range_list)

    def draw(self):
        plt.draw()

    @classmethod
    def update(cls, node):
        "Graph Update"
        node.plt_node.remove()
        node.circle.remove()
        node.plttxt.remove()

        cls.instantiate_circle(node)
        cls.instantiate_node(node)
        cls.instantiate_annotate(node)
        cls.draw()

    @classmethod
    def close_plot(cls):
        try:
            plt.close()
        except:
            pass


class Plot2D (object):
    ax = None
    lines = {}

    def __init__(self, **kwargs):
        self.instantiate_graph(**kwargs)

    def instantiate_graph(self, min_x, min_y, max_x, max_y, **kwargs):
        plt.ion()
        plt.figure(1)
        plt.title("Mininet-WiFi Graph")
        Plot2D.ax = plt.subplot(111)
        self.ax.set_xlabel('meters')
        self.ax.set_ylabel('meters')
        self.ax.set_xlim([min_x, max_x])
        self.ax.set_ylim([min_y, max_y])
        self.ax.grid(True)
        self.plot_graph(**kwargs)

    def plot_graph(self, nodes, links, **kwargs):
        debug('Enabling Graph...\n')
        for node in nodes:
            x, y, z = node.getxyz()
            self.instantiate_attrs(node)
            node.plt_node.set_data(x, y)
            node.set_text_pos(x, y)
            node.circle.center = x, y
            self.create_line(links)

    @classmethod
    def create_line(cls, links):
        for link in links:
            if 'wifi' not in str(link) and 'ITS' not in str(link):
                src = link.intf1.node
                dst = link.intf2.node
                if hasattr(src, 'position') and hasattr(dst, 'position'):
                    ls = link.intf1.params.get('ls', '-')
                    color = link.intf1.params.get('color', 'b')
                    lw = link.intf1.params.get('lw', 1)
                    Plot2D.add_line(src, dst, ls=ls, color=color, lw=lw)

    @classmethod
    def instantiate_attrs(cls, node):
        cls.instantiate_annotate(node)
        cls.instantiate_circle(node)
        cls.instantiate_node(node)
        node.update_2d()

    @classmethod
    def instantiate_annotate(cls, node, text=None):
        text = text if text is not None else node.name
        node.plttxt = Plot2D.ax.annotate(text, xy=(0, 0))

        # newer MPL versions (>=1.4) compatability
        if not hasattr(node.plttxt, 'xyann'):
            node.plttxt.xyann = node.plttxt.xytext

    @classmethod
    def instantiate_circle(cls, node):
        color = node.get_circle_color()
        node.circle = Plot2D.ax.add_patch(
            patches.Circle((0, 0), node.get_max_radius(),
                           fill=True, alpha=0.1, color=color))

    @classmethod
    def instantiate_node(cls, node):
        node.plt_node, = Plot2D.ax.plot(1, 1, marker='.', ms=5, color='black')

    @classmethod
    def add_line(cls, src, dst, ls='-', lw=1, color='b'):
        src_x = round(src.position[0], 2)
        src_y = round(src.position[1], 2)
        dst_x = round(dst.position[0], 2)
        dst_y = round(dst.position[1], 2)
        line = Plot2D.line2d([src_x, dst_x],
                             [src_y, dst_y],
                             color, ls=ls, lw=lw)
        conn_ = src.name + '-' + dst.name
        Plot2D.lines[conn_] = line
        Plot2D.line(line)

    @classmethod
    def line(cls, line):
        cls.ax.add_line(line)

    @staticmethod
    def line2d(nodesx, nodesy, color='', ls='-', lw=1):
        return plt.Line2D(nodesx, nodesy, color=color, ls=ls, lw=lw)

    @classmethod
    def close_plot(cls):
        try:
            plt.cla()
        except:
            pass

    @classmethod
    def draw(cls):
        plt.draw()

    @classmethod
    def scatter(cls, nodesx, nodesy):
        return plt.scatter(nodesx, nodesy, color='red', marker='s')

    @classmethod
    def line_txt(cls, x, y, i):
        title = 'Av.%s' % i
        plt.text(x, y, title, ha='left', va='bottom', fontsize=8, color='g')

    @classmethod
    def set_annotate_color(cls, node, color):
        node.plttxt.set_color(color)

    @classmethod
    def set_node_color(cls, node, color):
        node.plt_node.set_c(color)

    @classmethod
    def set_node_marker(cls, node, marker=''):
        node.plt_node.set_marker(marker)

    @classmethod
    def hide_line(cls, src, dst):
        conn_ = src.name + dst.name
        cls.lines[conn_].set_visible(False)

    @classmethod
    def show_line(cls, src, dst):
        conn_ = src.name + dst.name
        cls.lines[conn_].set_visible(True)


class PlotGraph(object):

    def __init__(self, **kwargs):
        warnings.filterwarnings("ignore")
        self.instantiate_graph(**kwargs)

    def instantiate_graph(self, **kwargs):
        if kwargs['min_z'] == 0 and kwargs['max_z'] == 0:
            Plot2D(**kwargs)
        else:
            PlotGraph.plot3d = True
            Plot3D(**kwargs)

    @classmethod
    def pause(cls):
        try:
            plt.pause(0.001)
        except:
            pass

