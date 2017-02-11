# pylint: disable=no-member, invalid-name
from abc import abstractmethod
from enum import Enum

from traitlets import Bool, Int, Unicode

from uchroma.color import ColorUtils
from uchroma.fx import BaseFX, FXModule
from uchroma.hardware import Hardware, Quirks
from uchroma.led import LED
from uchroma.traits import ColorTrait, UseEnumCaseless
from uchroma.types import BaseCommand
from uchroma.util import MagicalEnum



class FX(Enum):
    """
    All known lighting effects.

    Not all effects are available on all devices.
    """
    DISABLE = 0x00
    WAVE = 0x01
    REACTIVE = 0x02
    BREATHE = 0x03
    SPECTRUM = 0x04
    CUSTOM_FRAME = 0x05
    STATIC = 0x06
    GRADIENT = 0x0A
    SWEEP = 0x0C
    CIRCLE = 0x0D
    HIGHLIGHT = 0x10
    MORPH = 0x11
    FIRE = 0x12
    RIPPLE_SOLID = 0x13
    RIPPLE = 0x14
    SPECTRUM_BLADE = 0x1C
    STARLIGHT = 0x19

    ALIGNMENT = 0xFE
    RAINBOW = 0xFF


class ExtendedFX(Enum):
    """
    Enumeration of "extended" effect types and command identifiers

    These effects use a different command structure than the standard
    effects. Should not normally be used as part of the API.

    FIXME: This functionality is incomplete and untested
    """
    DISABLE = 0x00
    STATIC = 0x01
    BREATHE = 0x02
    SPECTRUM = 0x03
    WAVE = 0x04
    REACTIVE = 0x05
    STARLIGHT = 0x07
    CUSTOM_FRAME = 0x08



# Modes for the Wave effect
# The "chase" modes add a circular spin around the trackpad (if supported)
class Direction(MagicalEnum, Enum):
    """
    Enumeration of directions and arguments for some animated effects
    which pan across the device. The "chase" variants are only available
    on devices with an illuminated trackpad such as the Blade Pro, and
    produce a rotating animation around the trackpad.
    """
    RIGHT = 1
    LEFT = 2
    LEFT_CHASE = 3
    RIGHT_CHASE = 4


# Modes for starlight and breathe effects
class Mode(Enum):
    """
    Enumeration of modes and arguments for some animated effects which
    accept a variable number of colors.
    """
    RANDOM = 0
    SINGLE = 1
    DUAL = 2


class MultiModeFX(BaseFX):

    color1 = ColorTrait()
    color2 = ColorTrait()
    speed = Int(default_value=1, min=1, max=4)


    @abstractmethod
    def apply(self) -> bool:
        return False


    def _apply(self, effect) -> bool:
        if self.color1 is not None and self.color2 is not None:
            mode = Mode.DUAL.value
        elif self.color1 is not None:
            mode = Mode.SINGLE.value
        else:
            mode = Mode.RANDOM.value

        args = [mode]

        if self.speed is not None:
            args.append(self.speed)

        if self.color1 is not None:
            args.append(self.color1)

        if self.color2 is not None:
            args.append(self.color2)

        return self._fxmod.set_effect(effect, *args)


class StandardFX(FXModule):
    """
    Manages device lighting effects
    """

    class Command(BaseCommand):
        """
        Commands used to apply effects

        FIXME: Provide a way to determine the current effect
        """
        SET_EFFECT = (0x03, 0x0A, None)
        SET_EFFECT_EXTENDED = (0x0F, 0x02, None)


    def __init__(self, *args, **kwargs):
        super(StandardFX, self).__init__(*args, **kwargs)
        self._report = None


    def _set_effect_basic(self, effect: FX, *args, transaction_id: int=None) -> bool:
        if self._report is None:
            self._report = self._driver.get_report( \
                *StandardFX.Command.SET_EFFECT.value, transaction_id=transaction_id)

        self._report.args.clear()
        self._report.args.put_all([effect.value, *args])

        return self._driver.run_report(self._report)


    def _set_effect_extended(self, effect: ExtendedFX, *args) -> bool:
        return self._driver.run_command(StandardFX.Command.SET_EFFECT_EXTENDED, 0x01,
                                        LED.Type.BACKLIGHT, effect, *args, transaction_id=0x3F)


    def set_effect(self, effect: Enum, *args) -> bool:
        if self._driver.has_quirk(Quirks.EXTENDED_FX_CMDS):
            if effect.name in ExtendedFX.__members__:
                return self._set_effect_extended(ExtendedFX[effect.name], *args)
            return False
        return self._set_effect_basic(effect, *args)


    class DisableFX(BaseFX):
        description = Unicode('Disable all effects')

        def apply(self) -> bool:
            """
            Disables all running effects

            :return: True if successful
            """
            return self._fxmod.set_effect(FX.DISABLE)


    class StaticFX(BaseFX):
        description = Unicode('Static color')
        color = ColorTrait(default_value='green')

        def apply(self) -> bool:
            """
            Sets lighting to a static color

            :param color: The color to apply

            :return: True if successful
            """
            return self._fxmod.set_effect(FX.STATIC, self.color)


    class WaveFX(BaseFX):
        description = Unicode('Waves of color')
        direction = UseEnumCaseless(enum_class=Direction, default_value=Direction.RIGHT)

        def apply(self) -> bool:
            """
            Activates the "wave" effect

            :param direction: Optional direction for the effect, defaults to right

            :return: True if successful
            """
            return self._fxmod.set_effect(FX.WAVE, self.direction)


    class SpectrumFX(BaseFX):
        description = Unicode('Cycle thru all colors of the spectrum')
        def apply(self) -> bool:
            """
            Slowly cycles lighting thru all colors of the spectrum

            :return: True if successful
            """
            return self._fxmod.set_effect(FX.SPECTRUM)


    class ReactiveFX(BaseFX):
        description = Unicode('Keys light up when pressed')
        color = ColorTrait(default_value='skyblue')
        speed = Int(1, min=1, max=4)

        def apply(self) -> bool:
            """
            Lights up keys when they are pressed

            :param color: Color of lighting when keys are pressed
            :param speed: Speed (1-4) at which the keys should fade out

            :return: True if successful
            """
            return self._fxmod.set_effect(FX.REACTIVE, self.speed, self.color)


    class SweepFX(BaseFX):
        description = Unicode('Colors sweep across the device')
        color = ColorTrait(default_value='green')
        base_color = ColorTrait()
        speed = Int(default_value=15, min=1, max=30)
        direction = UseEnumCaseless(enum_class=Direction, default_value=Direction.RIGHT)

        def apply(self) -> bool:
            """
            Produces colors which sweep across the device

            :param color: The color to sweep with (defaults to light blue)
            :param base_color: The base color for the effect (defaults to black)
            :param direction: The direction for the sweep
            :param speed: Speed of the sweep
            :param preset: Predefined color pair to use. Invalid with color/base_color.

            :return: True if successful
            """
            return self._fxmod.set_effect(FX.SWEEP, self.direction, self.speed,
                                          self.base_color, self.color)


    class MorphFX(BaseFX):
        description = Unicode('Morphing colors when keys are pressed')
        color = ColorTrait(default_value='magenta')
        base_color = ColorTrait(default_value='blue')
        speed = Int(default_value=2, min=1, max=4)

        def apply(self) -> bool:
            """
            A "morphing" color effect when keys are pressed

            :param color: The color when keys are pressed (defaults to magenta)
            :param base_color: The base color for the effect (defaults to blue)
            :param speed: Speed of the sweep
            :param preset: Predefined color pair to use. Invalid with color/base_color.

            :return: True if successful
            """
            return self._fxmod.set_effect(FX.MORPH, 0x04, self.speed, self.base_color, self.color)


    class FireFX(BaseFX):
        description = Unicode('Keys on fire')
        color = ColorTrait(default_value='red')
        speed = Int(default_value=0x40, min=0x10, max=0x80)

        def apply(self) -> bool:
            """
            Animated fire!

            :param color: Color scheme of the fire
            :param speed: Speed of the fire

            :return: True if successful
            """
            return self._fxmod.set_effect(FX.FIRE, 0x01, self.speed, self.color)


    class RippleFX(BaseFX):
        description = Unicode('Ripple effect when keys are pressed')
        color = ColorTrait(default_value='green')
        speed = Int(default_value=3, min=1, max=8)

        def apply(self) -> bool:
            return self._fxmod.set_effect(FX.RIPPLE, 0x01, self.speed * 10, self.color)


    class RippleSolidFX(BaseFX):
        description = Unicode('Ripple effect on a solid background')
        color = ColorTrait(default_value='green')
        speed = Int(default_value=3, min=1, max=8)

        def apply(self) -> bool:
            return self._fxmod.set_effect(FX.RIPPLE_SOLID, 0x01, self.speed * 10, self.color)



    class StarlightFX(MultiModeFX):
        description = Unicode('Keys sparkle with color')
        def apply(self) -> bool:
            """
            Activate the "starlight" effect. Colors sparkle across the device.

            This effect allows up to two (optional) colors. If no colors are
            specified, random colors will be used.

            :param color1: First color
            :param color2: Second color
            :param speed: Speed of the effect
            :param preset: Predefined color pair, invalid when color1/color2 is supplied

            :return: True if successful
            """
            return self._apply(FX.STARLIGHT)


    class BreatheFX(MultiModeFX):
        description = Unicode('Colors pulse in and out')
        def apply(self) -> bool:
            """
            Activate the "breathe" effect. Colors pulse in and out.

            This effect allows up to two (optional) colors. If no colors are
            specified, random colors will be used.

            :param color1: First color
            :param color2: Second color
            :param preset: Predefined color pair, invalid when color1/color2 is supplied

            :return: True if successful
            """
            return self._apply(FX.BREATHE)


    class CustomFrameFX(BaseFX):
        description = Unicode('Display custom frame')
        hidden = Bool(True)

        def apply(self) -> bool:
            """
            Activate the custom frame currently in the device memory

            Called by the Frame class when commit() is called.

            :return: True if successful
            """
            varstore = 0x01
            tid = None

            # FIXME: This doesn't work.
            if self._driver.device_type == Hardware.Type.MOUSE:
                varstore = 0x00
                tid = 0x80
            return self._fxmod.set_effect(FX.CUSTOM_FRAME, varstore)


    class RainbowFX(BaseFX):
        description = Unicode('Rainbow of hues')
        stagger = Int(default_value=4, min=0, max=100)
        length = Int(default_value=75, min=20, max=360)

        def apply(self) -> bool:
            """
            Show a rainbow of colors across the device

            Uses the Frame interface. Will change when device characteristics
            are implemented.

            :return: True if successful
            """
            if not self._driver.has_matrix:
                return False

            frame = self._driver.frame_control

            layer = frame.create_layer()

            data = []
            gradient = ColorUtils.hue_gradient( \
                self.length, layer.width + (layer.height * self.stagger))
            for row in range(0, layer.height):
                data.append([gradient[(row * self.stagger) + col] for col in range(0, layer.width)])

            layer.put_all(data)
            frame.commit([layer])

            return True


    class AlignmentFX(BaseFX):
        description = Unicode('Alignment test pattern')
        hidden = Bool(True)
        cur_row = Int(min=0, default_value=0)
        cur_col = Int(min=0, default_value=0)

        def apply(self) -> bool:
            first = 'red'
            single = 'white'
            colors = ['yellow', 'green', 'purple', 'blue']

            frame = self._driver.frame_control
            layer = frame.create_layer()

            for row in range(0, layer.height):
                for col in range(0, layer.width):
                    if col == 0:
                        color = first
                    else:
                        color = colors[int((col - 1) % len(colors))]
                    layer.put(row, col, color)

            layer.put(self.cur_row, self.cur_col, single)
            frame.debug_opts['debug_position'] = (self.cur_row, self.cur_col)

            frame.commit([layer])

            return True