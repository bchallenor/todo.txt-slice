#!/usr/bin/env python3
from datetime import date
import imp
import os.path
import unittest

slice = imp.load_source("slice", "slice")


class VirtualTempDir:
  def __init__(self, path):
    self.__path = path
    self.clean_exit = False

  def __enter__(self):
    return self.__path

  def __exit__(self, exc_type, exc_value, traceback):
    self.clean_exit = exc_type is None


class VirtualTodoEnv(unittest.TestCase):
  todo_file_name = "todo.txt"
  __slice_dir_path = "SLICE"
  __slice_file_path = os.path.join(__slice_dir_path, todo_file_name)
  todo_dir_path = "TODO"
  todo_file_path = os.path.join(todo_dir_path, todo_file_name)
  today = date(2000, 1, 1)

  def __init__(self, todo_pre, slice_pre, slice_post, todo_post, date_on_add, preserve_line_numbers, disable_filter):
    unittest.TestCase.__init__(self)

    self.__todo_pre = todo_pre
    self.__slice_pre = slice_pre
    self.__slice_post = slice_post
    self.__todo_post = todo_post

    self.__slice_dir = VirtualTempDir(self.__slice_dir_path)
    self.__slice_file_path_written = False
    self.__todo_file_path_written = False

    self.date_on_add = date_on_add
    self.default_create_date = self.today if date_on_add else None
    self.preserve_line_numbers = preserve_line_numbers
    self.disable_filter = disable_filter

  def read_lines(self, path):
    if path == self.todo_file_path:
      return self.__todo_pre
    elif path == self.__slice_file_path:
      return self.__slice_post
    else:
      self.fail("attempt to read unknown path: %s" % path)

  def write_lines(self, path, lines):
    if path == self.todo_file_path:
      self.assertEqual(self.__todo_post, lines, msg = "Todo file content does not match expected content")
      self.__todo_file_path_written = True
    elif path == self.__slice_file_path:
      self.assertEqual(self.__slice_pre, lines, msg = "Slice file content does not match expected content")
      self.__slice_file_path_written = True
    else:
      self.fail("attempt to write unknown path: %s" % path)

  def create_temp_dir(self):
    return self.__slice_dir

  def launch_editor(self, path):
    self.assertEqual(self.__slice_file_path, path)

  def assert_success(self):
    self.assertTrue(self.__slice_dir.clean_exit, msg = "Expected slice directory to be used and cleaned up")
    self.assertTrue(self.__slice_file_path_written, msg = "Expected slice file to be written")
    self.assertTrue(self.__todo_file_path_written, msg = "Expected todo file to be written")


class SliceTest(unittest.TestCase):
  action_name = "slice"

  def run_test(
      self,
      filter_args = [],
      expect_early_exit = False,
      todo_pre = None,
      slice_pre = None,
      slice_post = None,
      todo_post = None,
      date_on_add = False,
      preserve_line_numbers = False,
      disable_filter = False
      ):

    args = ["dummy.py"]

    if self.action_name is not None:
      args.append(self.action_name)

      if self.filter_name is not None:
        args.append(self.filter_name)
        args.extend(filter_args)

    env = VirtualTodoEnv(
        todo_pre = todo_pre,
        slice_pre = slice_pre,
        slice_post = slice_post if slice_post is not None else slice_pre,
        todo_post = todo_post if todo_post is not None else todo_pre,
        date_on_add = date_on_add,
        preserve_line_numbers = preserve_line_numbers,
        disable_filter = disable_filter
        )

    slice.main(env, args)

    if not expect_early_exit:
      env.assert_success()


class SliceMatchTest(SliceTest):
  filter_name = "match"

  def test_single_task(self):
    self.run_test(
        todo_pre = [
          "task"
          ],
        slice_pre = [
          "i:1 task"
          ]
        )

  def test_completed_tasks_are_hidden(self):
    self.run_test(
        todo_pre = [
          "x 2000-01-01 done"
          ],
        slice_pre = [
          ]
        )


if __name__ == "__main__":
  unittest.main()

