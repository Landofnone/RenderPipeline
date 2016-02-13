"""

RenderPipeline

Copyright (c) 2014-2016 tobspr <tobias.springer1@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
 	 	    	 	
"""
from six import iteritems

from panda3d.core import PTAFloat, PTALVecBase3f, PTALMatrix4f, PTALVecBase2f
from panda3d.core import PTALVecBase4f, PTALMatrix3f, PTAInt, TypeRegistry

from ..rp_object import RPObject

__all__ = ["BaseUBO", "SimpleUBO", "ShaderUBO"]

class BaseUBO(RPObject):
    """ Base class for UBO's """

    def __init__(self):
        RPObject.__init__(self)


class SimpleUBO(BaseUBO):

    """ Simplest possible uniform buffer which just stores a set of values """

    def __init__(self, name):
        BaseUBO.__init__(self)
        self._inputs = {}
        self._name = name

    def add_input(self, name, value):
        """ Adds a new input to the UBO """
        self._inputs[name] = value

    def get_name(self):
        """ Returns the name of the UBO """
        return self._name

    def bind_to(self, target):
        """ Binds the UBO to a target """
        for key, val in iteritems(self._inputs):
            target.set_shader_input(self._name + "." + key, val)


class ShaderUBO(BaseUBO):

    """ Interface to shader uniform blocks, using PTA's to efficiently store
    and update values. """

    _UBO_BINDING_INDEX = 0

    @classmethod
    def ubos_supported(cls):
        """ Checks whether the panda3d build currently used supports UBOs """
        return bool(TypeRegistry.ptr().find_type("GLUniformBufferContext"))

    def __init__(self, name):
        """ Constructs the UBO with a given name """
        BaseUBO.__init__(self)
        self._ptas = {}
        self._name = name
        self._use_ubo = self.ubos_supported()

        # Acquire a unique index for each UBO to store its binding
        self._bind_id = ShaderUBO._UBO_BINDING_INDEX
        ShaderUBO._UBO_BINDING_INDEX += 1

        self.debug("Native UBO support =", self._use_ubo)

    def register_pta(self, name, type):
        """ Registers a new input, type should be a glsl type """
        pta_handle = self._glsl_type_to_pta(type).empty_array(1)
        self._ptas[name] = pta_handle

    def get_name(self):
        """ Returns the name of the UBO """
        return self._name

    def _pta_to_glsl_type(self, pta_handle):
        """ Converts a PtaXXX to a glsl type """
        mappings = {
            PTAInt: "int",
            PTAFloat: "float",
            PTALVecBase2f: "vec2",
            PTALVecBase3f: "vec3",
            PTALVecBase4f: "vec4",
            PTALMatrix3f: "mat3",
            PTALMatrix4f: "mat4",
        }
        for mapping, glsl_type in iteritems(mappings):
            if isinstance(pta_handle, mapping):
                return glsl_type
        self.warn("Unrecognized PTA type:", pta_handle)
        return "float"

    def _glsl_type_to_pta(self, glsl_type):
        """ Converts a glsl type to a PtaXXX type """
        mappings = {
            "int": PTAInt,
            "float": PTAFloat,
            "vec2": PTALVecBase2f,
            "vec3": PTALVecBase3f,
            "vec4": PTALVecBase4f,
            "mat3": PTALMatrix3f,
            "mat4": PTALMatrix4f,
        }
        if glsl_type in mappings:
            return mappings[glsl_type]
        self.warn("Unrecognized glsl type:", glsl_type)
        return None

    def bind_to(self, target):
        """ Binds all inputs of this UBO to the given target, which may be
        either a RenderTarget or a NodePath """

        for pta_name, pta_handle in iteritems(self._ptas):
            if self._use_ubo:
                target.set_shader_input(self._name + "_UBO." + pta_name, pta_handle)
            else:
                target.set_shader_input(self._name + "." + pta_name, pta_handle)

    def update_input(self, name, value):
        """ Updates an existing input """
        self._ptas[name][0] = value

    def get_input(self, name):
        """ Returns the value of an existing input """
        return self._ptas[name][0]

    def generate_shader_code(self):
        """ Generates the GLSL shader code to use the UBO """

        content = "#pragma once\n\n"
        content += "// Autogenerated by RenderingPipeline\n"
        content += "// Do not edit! Your changes will be lost.\n\n"

        structs = {}
        inputs = []

        for input_name, handle in iteritems(self._ptas):
            parts = input_name.split(".")

            # Single input, simply add it to the input list
            if len(parts) == 1:
                inputs.append(self._pta_to_glsl_type(handle) + " " + input_name + ";")

            # Nested input, like Scattering.sun_color
            elif len(parts) == 2:
                struct_name = parts[0]
                actual_input_name = parts[1]
                if struct_name in structs:
                    # Struct is already defined, add member definition
                    structs[struct_name].append(
                        self._pta_to_glsl_type(handle) + " " + actual_input_name + ";")
                else:
                    # Construct a new struct and add it to the list of inputs
                    inputs.append(struct_name + "_UBOSTRUCT " + struct_name + ";")
                    structs[struct_name] = [
                        self._pta_to_glsl_type(handle) + " " + actual_input_name + ";"
                    ]

            # Nested input, like Scattering.some_setting.sun_color, not supported yet
            else:
                self.warn("Structure definition too nested, not supported (yet):", input_name)

        # Add structures
        for struct_name, members in iteritems(structs):
            content += "struct " + struct_name + "_UBOSTRUCT {\n"
            for member in members:
                content += " " * 4 + member + "\n"
            content += "};\n\n"

        # Add actual inputs
        if len(inputs) < 1:
            self.debug("No UBO inputs present for", self._name)
        else:
            if self._use_ubo:
                content += "layout(shared, binding=" + str(self._bind_id) + ") uniform " + self._name + "_UBO {\n"
                for ipt in inputs:
                     content += " " * 4 + ipt + "\n"
                content += "} " + self._name + ";\n"
            else:
                content += "uniform struct {\n"
                for ipt in inputs:
                     content += " " * 4 + ipt + "\n"
                content += "} " + self._name + ";\n"

        content += "\n"
        return content