# Copyright 2017 The dm_control Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or  implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============================================================================

r"""Automatically generates ctypes Python bindings for MuJoCo.

Parses mjdata.h, mjmodel.h, mjrender.h, mjvisualize.h, mjxmacro.h and mujoco.h;
generates the following Python source files:

  constants.py:  constants
  enums.py:      enums
  sizes.py:      size information for dynamically-shaped arrays
  types.py:      ctypes declarations for structs
  wrappers.py:   low-level Python wrapper classes for structs (these implement
                 getter/setter methods for struct members where applicable)
  functions.py:  ctypes function declarations for MuJoCo API functions

Example usage:

  autowrap --header_paths='/path/to/mjmodel.h /path/to/mjdata.h ...' \
           --output_dir=/path/to/mjbindings
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections
import os

# Internal dependencies.

from absl import app
from absl import flags
from absl import logging

from dm_control.autowrap import binding_generator
from dm_control.autowrap import codegen_util

import six

FLAGS = flags.FLAGS

flags.DEFINE_spaceseplist(
    "header_paths", None,
    "Space-separated list of paths to MuJoCo header files.")

flags.DEFINE_string("output_dir", None,
                    "Path to output directory for wrapper source files.")


def main(unused_argv):
  # Get the path to the xmacro header file.
  xmacro_hdr_path = None
  for path in FLAGS.header_paths:
    if path.endswith("mjxmacro.h"):
      xmacro_hdr_path = path
      break
  if xmacro_hdr_path is None:
    logging.fatal("List of inputs must contain a path to mjxmacro.h")

  srcs = codegen_util.UniqueOrderedDict()
  for p in sorted(FLAGS.header_paths):
    with open(p, "r") as f:
      srcs[p] = f.read()

  # consts_dict should be a codegen_util.UniqueOrderedDict.
  # This is a temporary workaround due to the fact that the parser does not yet
  # handle nested `#if define(predicate)` blocks, which results in some
  # constants being parsed twice. We therefore can't enforce the uniqueness of
  # the keys in `consts_dict`. As of MuJoCo v1.30 there is only a single problem
  # block beginning on line 10 in mujoco.h, and a single constant is affected
  # (MJAPI).
  consts_dict = collections.OrderedDict()

  # These are commented in `mjdata.h` but have no macros in `mjxmacro.h`.
  hints_dict = codegen_util.UniqueOrderedDict({"buffer": ("nbuffer",),
                                               "stack": ("nstack",)})

  parser = binding_generator.BindingGenerator(
      consts_dict=consts_dict, hints_dict=hints_dict)

  # Parse enums.
  for pth, src in six.iteritems(srcs):
    if pth is not xmacro_hdr_path:
      parser.parse_enums(src)

  # Parse constants and type declarations.
  for pth, src in six.iteritems(srcs):
    if pth is not xmacro_hdr_path:
      parser.parse_consts_typedefs(src)

  # Get shape hints from mjxmacro.h.
  parser.parse_hints(srcs[xmacro_hdr_path])

  # Parse structs.
  for pth, src in six.iteritems(srcs):
    if pth is not xmacro_hdr_path:
      parser.parse_structs(src)

  # Parse functions.
  for pth, src in six.iteritems(srcs):
    if pth is not xmacro_hdr_path:
      parser.parse_functions(src)

  # Parse global strings and function pointers.
  for pth, src in six.iteritems(srcs):
    if pth is not xmacro_hdr_path:
      parser.parse_global_strings(src)
      parser.parse_function_pointers(src)

  # Create the output directory if it doesn't already exist.
  if not os.path.exists(FLAGS.output_dir):
    os.makedirs(FLAGS.output_dir)

  # Generate Python source files and write them to the output directory.
  parser.write_consts(os.path.join(FLAGS.output_dir, "constants.py"))
  parser.write_enums(os.path.join(FLAGS.output_dir, "enums.py"))
  parser.write_types(os.path.join(FLAGS.output_dir, "types.py"))
  parser.write_wrappers(os.path.join(FLAGS.output_dir, "wrappers.py"))
  parser.write_funcs_and_globals(os.path.join(FLAGS.output_dir, "functions.py"))
  parser.write_index_dict(os.path.join(FLAGS.output_dir, "sizes.py"))

if __name__ == "__main__":
  flags.mark_flag_as_required("header_paths")
  flags.mark_flag_as_required("output_dir")
  app.run(main)
