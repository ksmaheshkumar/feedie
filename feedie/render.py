import gobject
import gtk
import pango
import locale
import time
import cairo
from math import pi
from feedie import graphics, util

rsva = {
  'list-bg': (
    (.00, 0.0000, 0.9020, 1.0), # neither
    (.00, 0.0000, 0.9020, 1.0), # only selected
    (.00, 0.0652, 0.9020, 1.0), # only focused
    (.00, 0.0652, 0.9020, 1.0), # selected and focused
  ),
  'item-bg-bottom': (
    (.00, 0.0000, 0.5150, 1.0),
    (.00, 0.0000, 0.5150, 1.0),
    (.00, 0.8230, 0.7290, 1.0),
    (.00, 0.8230, 0.7290, 1.0),
  ),
  'item-fg': (
    (.00, 0.0000, 0.1000, 1.0),
    (.00, 0.0000, 1.0000, 1.0),
    (.00, 0.0000, 0.2000, 1.0),
    (.00, 0.0000, 1.0000, 1.0),
  ),
  'item-fg-shadow': (
    (.00, 0.0000, 0.0000, 0.6),
    (.00, 0.0000, 0.0000, 0.6),
    (.00, 0.0000, 0.0000, 0.6),
    (.00, 0.0000, 0.0000, 0.6),
  ),
  'heading-fg': (
    (.00, 0.2346, 0.5840, 1.0),
    (.00, 0.2346, 0.5840, 1.0),
    (.00, 0.2346, 0.5840, 1.0),
    (.00, 0.2346, 0.5840, 1.0),
  ),
  'heading-fg-shadow': (
    (.00, 0.0000, 0.9500, 1.0),
    (.00, 0.0000, 0.9500, 1.0),
    (.00, 0.0000, 0.9500, 1.0),
    (.00, 0.0000, 0.9500, 1.0),
  ),
  'pill-bg': (
    (.00, 0.4327, 0.8157, 1.0),
    (.00, 0.0000, 1.0000, 1.0),
    (.00, 0.4327, 0.8157, 1.0),
    (.00, 0.0000, 1.0000, 1.0),
  ),
  'pill-fg': (
    (.00, 0.0000, 1.0000, 1.0),
    (.00, 0.0000, 0.3500, 1.0),
    (.00, 0.0000, 1.0000, 1.0),
    (.00, 0.0000, 0.3500, 1.0),
  ),
  'pulse': (
    (.00, 0.0000, 0.4000, 1.0),
    (.54, 0.5789, 0.9500, 1.0),
    (.00, 0.0000, 0.4000, 1.0),
    (.54, 0.5789, 0.9500, 1.0),
  ),
  'spinner': (
    (.00, 0.0652, 0.4000, 1.0),
    (.00, 0.0000, 1.0000, 1.0),
    (.00, 0.0652, 0.4000, 1.0),
    (.00, 0.0000, 1.0000, 1.0),
  ),
}

def color_rgba(stv, name, selected=True, focused=True):
  i = 2 * int(bool(focused)) + int(bool(selected))
  return stv.color[name][i]

def color_rgb(stv, name, selected=True, focused=True):
  return color_rgba(stv, name, selected=selected, focused=focused)[:3]

def set_color(stv, ctx, name, selected=True, focused=True):
  rgba = color_rgba(stv, name, selected=selected, focused=focused)
  ctx.set_source_rgba(*rgba)

class Item(object):
  width = 0
  height = 0

  def render(self, ctx, area, flags):
    pass

  def dynamic_width(self, ctx, area):
    return self.width

class ItemIndent(Item):
  @property
  def width(self):
    is_heading = self.cellr._props['is-heading']
    if is_heading: return 8
    return 18

class ItemShim(Item):
  def __init__(self, width=0, height=0):
    self.width = width
    self.height = height

class ItemIcon(Item):
  @property
  def width(self):
    icon = self.cellr._props['icon']
    if icon: return 16
    return 0

  @property
  def height(self):
    icon = self.cellr._props['icon']
    if icon: return 16
    return 0

  def render(self, ctx, area, flags):
    icon = self.cellr._props['icon']
    if not icon: return

    # Offset to center the icon
    dx = abs(area.width - icon.get_width()) / 2
    dy = abs(area.height - icon.get_height()) / 2

    ctx.set_source_pixbuf(icon, area.x + dx, area.y + dy)
    ctx.paint()

def draw_text(ctx, fd, area, text, dx, dy):
  layout = ctx.create_layout()
  layout.set_width(area.width * pango.SCALE)
  layout.set_wrap(False)
  layout.set_ellipsize(pango.ELLIPSIZE_END)
  layout.set_font_description(fd)
  layout.set_text(text)
  text_width, text_height = layout.get_pixel_size()
  if text_width > area.width: return

  cy = (area.height - text_height) / 2

  ctx.move_to(area.x + dx, area.y + cy + dy)
  ctx.show_layout(layout)

class ItemText(Item):
  width = 0

  @property
  def height(self):
    fd = self.cellr.widget.get_style().font_desc.copy()
    p_ctx = self.cellr.widget.get_pango_context()
    metrics = p_ctx.get_metrics(fd, None)
    approx = (metrics.get_ascent() + metrics.get_descent()) / pango.SCALE
    return max(approx + approx / 2 - 1, 10)

    return 22 # TODO measure text and add leading

  def render(self, ctx, area, flags):
    stv = self.cellr.widget
    is_selected = bool(flags & gtk.CELL_RENDERER_SELECTED)
    unread = self.cellr._props['unread']

    if self.cellr._props['is-heading']:
      text = self.cellr._props['text']
      fd = self.cellr.widget.get_style().font_desc.copy()
      fd.set_weight(700)

      set_color(stv, ctx, 'heading-fg-shadow')
      draw_text(ctx, fd, area, text, 0, 1)

      set_color(stv, ctx, 'heading-fg')
      draw_text(ctx, fd, area, text, 0, 0)
    else:
      # Abusing "focused" here...
      is_focused = unread > 0

      text = self.cellr._props['text']
      weight = (500, 600)[is_selected or is_focused]
      fd = self.cellr.widget.get_style().font_desc.copy()
      fd.set_weight(weight)

      if is_selected:
        set_color(stv, ctx, 'item-fg-shadow', selected=is_selected)
        draw_text(ctx, fd, area, text, 0, 1)

      set_color(stv, ctx, 'item-fg',
          selected=is_selected, focused=is_focused)
      draw_text(ctx, fd, area, text, 0, 0)


class ItemPill(Item):
  _padding = 5
  _tb_margin = 3

  def dynamic_width(self, ctx, area):
    unread = self.cellr._props['unread']
    if not unread: return 0

    layout = ctx.create_layout()
    layout.set_wrap(False)
    fd = self.cellr.widget.get_style().font_desc.copy()
    fd.set_weight(700)
    layout.set_font_description(fd)
    layout.set_text(locale.format('%d', unread, grouping=True))
    text_width, text_height = layout.get_pixel_size()
    pill_height = area.height - 2 * self._tb_margin
    pill_width = max(text_width + 2 * self._padding, int(1.5 * pill_height))
    return pill_width


  def render(self, ctx, area, flags):
    stv = self.cellr.widget
    is_selected = bool(flags & gtk.CELL_RENDERER_SELECTED)
    unread = self.cellr._props['unread']

    layout = ctx.create_layout()
    layout.set_wrap(False)
    fd = self.cellr.widget.get_style().font_desc.copy()
    fd.set_weight(700)
    layout.set_font_description(fd)
    layout.set_text(locale.format('%d', unread, grouping=True))
    text_width, text_height = layout.get_pixel_size()
    pill_height = area.height - 2 * self._tb_margin
    pill_width = max(text_width + 2 * self._padding, int(1.5 * pill_height))

    text_offset = (pill_width - text_width) * 0.5

    cx = (area.width - text_width) * 0.5
    cy = (area.height - text_height) * 0.5

    set_color(stv, ctx, 'pill-bg', selected=is_selected)
    graphics.rounded_rect(ctx, area.x,
        area.y + self._tb_margin, pill_width, pill_height, 1000)
    ctx.fill()

    set_color(stv, ctx, 'pill-fg', selected=is_selected)
    ctx.move_to(area.x + cx, area.y + cy)
    ctx.show_layout(layout)

class ItemProg(Item):
  @property
  def width(self):
    prog = self.cellr._props['progress']
    if prog > 0: return 16
    return 0

  @property
  def height(self):
    prog = self.cellr._props['progress']
    if prog > 0: return 16
    return 0

  def render(self, ctx, area, flags):
    stv = self.cellr.widget
    prog = self.cellr._props['progress']
    is_selected = bool(flags & gtk.CELL_RENDERER_SELECTED)

    r = 8
    cx = area.x + area.width * 0.5
    cy = area.y + area.height * 0.5

    set_color(stv, ctx, 'pill-bg', selected=is_selected)
    ctx.new_sub_path()
    ctx.arc(cx, cy, r, 0, 2*pi)
    ctx.set_line_width(1)
    ctx.fill()

    set_color(stv, ctx, 'pill-fg', selected=is_selected)
    ctx.move_to(cx, cy)
    ctx.arc(cx, cy, r - 2, (2 * pi * prog / 100) - (pi/2), -pi/2)
    ctx.line_to(cx, cy)
    ctx.fill()

class ItemSpin(Item):
  spin_speed = 70 # in degrees/second

  @property
  def width(self):
    prog = self.cellr._props['progress']
    if prog < 0: return 16
    return 0

  @property
  def height(self):
    prog = self.cellr._props['progress']
    if prog < 0: return 16
    return 0

  def render(self, ctx, area, flags):
    stv = self.cellr.widget
    began = self.cellr._props['spin-start']
    is_selected = bool(flags & gtk.CELL_RENDERER_SELECTED)

    r = 8
    cx = area.x + area.width * 0.5
    cy = area.y + area.height * 0.5

    dt = time.time() - began
    rho = int(dt * self.spin_speed) % 360

    set_color(stv, ctx, 'spinner', selected=is_selected)

    ctx.new_sub_path()
    ctx.arc(cx, cy, r - 2,
        (2 * pi * rho / 360),
        (2 * pi * rho / 360) + (2*pi/3))

    ctx.new_sub_path()
    ctx.arc(cx, cy, r - 2,
        (2 * pi * rho / 360) + (pi),
        (2 * pi * rho / 360) + (5*pi/3))

    ctx.set_line_width(2.5)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()

class CellRendererItems(gtk.GenericCellRenderer):
  __gproperties__ = {
    'text': (str, 'Text', 'Text', '(unknown)', gobject.PARAM_WRITABLE),
    'unread': (int, 'Unread', 'Unread Count', 0, 1000000, 0,
        gobject.PARAM_WRITABLE),
    'progress': (int, 'Progress', 'Progress', -1, 100, 0,
        gobject.PARAM_WRITABLE),
    'spin-start': (float, 'Spin Start', 'Spin Start', 0, 10000000000, 0,
        gobject.PARAM_WRITABLE),
    'spin-update': (int, 'Spin Update', 'Spin Update', 0, 1000000000, 0,
        gobject.PARAM_WRITABLE),
    'icon': (gtk.gdk.Pixbuf, 'Icon', 'Icon', gobject.PARAM_WRITABLE),
    'is-heading': (bool, 'Is Heading', 'Is Heading', False,
        gobject.PARAM_WRITABLE),
  }

  _padding_left = 10
  _padding_between = 2

  _start_items = (
    ItemIndent(),
    ItemIcon(),
  )

  _flex_item = ItemText()

  _end_items = (
    ItemShim(width=2),
    ItemPill(),
    ItemProg(),
    ItemSpin(),
  )

  def __init__(self):
    gtk.GenericCellRenderer.__init__(self)
    self._props = {}
    for r in self._items:
      r.cellr = self

  @property
  def _items(self):
    return self._start_items + (self._flex_item,) + self._end_items

  def on_get_size(self, widget, cell_area):
    self.widget = widget
    width = sum(x.width for x in self._items)
    height = max(x.height for x in self._items)
    del self.widget
    return (0, 0, width, height)

  def on_render(self, window, widget, bg_area, cell_area, expose_area, flags):
    try:
      self.widget = widget
      ctx = window.cairo_create()

      # Render background
      if flags & gtk.CELL_RENDERER_SELECTED:
        bot_grad_color = color_rgb(widget, 'item-bg-bottom',
            focused=widget.props.has_focus)
        top_grad_color = util.mix(0.30, bot_grad_color, (1, 1, 1))
        top_line_color = util.mix(0.18, bot_grad_color, (1, 1, 1))

        linear = cairo.LinearGradient(0, bg_area.y,
                                      0, bg_area.y + bg_area.height)
        linear.add_color_stop_rgb(0, *top_grad_color)
        linear.add_color_stop_rgb(1, *bot_grad_color)
        ctx.set_source(linear)
        ctx.rectangle(*bg_area)
        ctx.fill()

        ctx.set_source_rgb(*top_line_color)
        ctx.move_to(bg_area.x + 0.5, bg_area.y + 0.5)
        ctx.line_to(bg_area.x + bg_area.width + 0.5, bg_area.y + 0.5)
        ctx.set_line_width(1)
        ctx.stroke()

      ctx.rectangle(*expose_area)
      ctx.clip()

      area = gtk.gdk.Rectangle(*cell_area)
      for item in self._start_items:
        w = item.dynamic_width(ctx, area)
        if w:
          item_area = gtk.gdk.Rectangle(area.x, area.y, w, area.height)
          item.render(ctx, item_area, flags)

          w += self._padding_between
          area.x += w
          area.width -= w
          if not area.width: return

      for item in self._end_items:
        w = item.dynamic_width(ctx, area)
        if w and w < area.width and area.width > 50:
          item_area = gtk.gdk.Rectangle(area.x + area.width - w, area.y,
              w, area.height)
          item.render(ctx, item_area, flags)

          w += self._padding_between
          area.width -= w
          if not area.width: return

      item = self._flex_item
      if item:
        item.render(ctx, area, flags)
        if not area.width: return

    finally:
      del self.widget

  def on_activate(self, event, widget, path, bg_area, cell_area, flags):
    pass

  def on_start_editing(self, event, widget, path, bg_area, cell_area, flags):
    pass


  def do_set_property(self, k, v):
    self._props[k.name] = v

