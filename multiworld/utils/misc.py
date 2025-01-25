import functools
import math

from typing import Tuple


def are_within_radius(tuple0: Tuple[int, int], tuple1: Tuple[int, int], radius: float):
    distance = math.sqrt(sum((a - b) ** 2 for a, b in zip(tuple0, tuple1)))
    return distance <= radius


@functools.cache
def front_pos(agent_x: int, agent_y: int, agent_dir: int):
    """
    Get the position in front of an agent.
    """
    direction_radians = math.radians(agent_dir)

    delta_x = math.cos(direction_radians)
    delta_y = math.sin(direction_radians)

    new_x = agent_x + round(delta_x)
    new_y = agent_y + round(delta_y)

    return new_x, new_y


class PropertyAlias(property):
    """
    A class property that is an alias for an attribute property.

    Instead of::

        @property
        def x(self):
            self.attr.x

        @x.setter
        def x(self, value):
            self.attr.x = value

    we can simply just declare::

        x = PropertyAlias('attr', 'x')
    """

    def __init__(
        self, attr_name: str, attr_property_name: str, doc: str | None = None
    ) -> None:
        """
        Parameters
        ----------
        attr_name : str
            Name of the base attribute
        attr_property : property
            Property from the base attribute class
        doc : str
            Docstring to append to the property's original docstring
        """
        prop = lambda obj: getattr(type(getattr(obj, attr_name)), attr_property_name)
        fget = lambda obj: prop(obj).fget(getattr(obj, attr_name))
        fset = lambda obj, value: prop(obj).fset(getattr(obj, attr_name), value)
        fdel = lambda obj: prop(obj).fdel(getattr(obj, attr_name))
        super().__init__(fget, fset, fdel, doc=doc)
        self.__doc__ = doc
