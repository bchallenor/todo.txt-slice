#!/usr/bin/env python3
from contextlib import contextmanager
from datetime import date
import imp
import logging
import os.path
import unittest

slice = imp.load_source("slice", "slice")
AbstractTodoEnv = slice.AbstractTodoEnv
Tag = slice.Tag
ContextTag = slice.ContextTag
ProjectTag = slice.ProjectTag
KeyValueTag = slice.KeyValueTag


@contextmanager
def capture(log, level):
  records = []

  class MemoryHandler(logging.Handler):
    def emit(self, record):
      records.append(record)

  h = MemoryHandler()
  h.setLevel(level)
  log.addHandler(h)

  yield records

  log.removeHandler(h)


class VirtualTodoEnv(AbstractTodoEnv, unittest.TestCase):
  __editor_path = "EDITOR"
  __todo_file_name = "todo.txt"
  __edit_dir_path = "EDIT"
  __edit_file_path = os.path.join(__edit_dir_path, __todo_file_name)
  __todo_dir_path = "TODO"
  __todo_file_path = os.path.join(__todo_dir_path, __todo_file_name)

  def __init__(self, expect_clean_exit, todo0, edit0, edit1, todo1, strip_edit0_comments, export, unset):
    unittest.TestCase.__init__(self)

    self.__expect_clean_exit = expect_clean_exit

    self.__todo0 = todo0
    self.__edit0 = edit0
    self.__edit1 = edit1
    self.__todo1 = todo1

    self.__strip_edit0_comments = strip_edit0_comments

    self.__edit_dir_deleted = False
    self.__edit_file_path_written = False
    self.__todo_file_path_written = False

    os_environ = {
        "TODO_DIR": self.__todo_dir_path,
        "TODO_FILE": self.__todo_file_path,
        "EDITOR": self.__editor_path,
        "TODOTXT_DATE_ON_ADD": "0",
        "TODOTXT_PRESERVE_LINE_NUMBERS": "1",
        "TODOTXT_DISABLE_FILTER": "0",
        }

    os_environ.update(export)

    for key in unset:
      del os_environ[key]

    AbstractTodoEnv.__init__(self, os_environ)

  def today(self):
    return date(2000, 1, 1)

  def read_lines(self, path):
    if path == self.__todo_file_path:
      return self.__todo0
    elif path == self.__edit_file_path:
      return self.__edit1
    else:
      self.fail("attempt to read unknown path: %s" % path)

  def write_lines(self, path, lines):
    if path == self.__todo_file_path:
      self.assertEqual(self.__todo1, lines, msg = "Todo file content does not match expected content")
      self.__todo_file_path_written = True
    elif path == self.__edit_file_path:
      testable_lines = [line for line in lines if not line.startswith("#") and line != ""] if self.__strip_edit0_comments else lines
      self.assertEqual(self.__edit0, testable_lines, msg = "Slice file content does not match expected content")
      self.__edit_file_path_written = True
    else:
      self.fail("attempt to write unknown path: %s" % path)

  @contextmanager
  def create_temp_dir(self):
    self.__edit_dir_deleted = False
    yield self.__edit_dir_path
    self.__edit_dir_deleted = True

  def subprocess_check_call(self, path, args):
    self.assertEqual(self.__editor_path, path)
    self.assertEqual([self.__edit_file_path], args)

  def print_diff(self, id, max_id_len, task_a, task_b):
    self.assertLessEqual(len(str(id)), max_id_len, msg = "Expected id (%d) to have length <= %d" % (id, max_id_len))
    self.assertNotEqual(task_a, task_b)

  def assert_success(self):
    if self.__expect_clean_exit:
      self.assertTrue(self.__edit_dir_deleted, msg = "Expected edit directory to be used and cleaned up")
      self.assertTrue(self.__edit_file_path_written, msg = "Expected edit file to be written")
      changes = self.__todo0 != self.__todo1
      if changes:
        self.assertTrue(self.__todo_file_path_written, msg = "Expected todo file to be written")
      else:
        self.assertFalse(self.__todo_file_path_written, msg = "Expected todo file to be untouched as there were no changes")
    else:
      self.assertFalse(self.__todo_file_path_written, msg = "Expected todo file to be untouched")


class TagTest(unittest.TestCase):
  def test_join_tokens(self):
    a = ContextTag("a")
    b = ContextTag("b")

    # trivial cases
    self.__test_join_tokens([], "")
    self.__test_join_tokens([" "], "")
    self.__test_join_tokens(["\t"], "")
    self.__test_join_tokens(["x"], "x")
    self.__test_join_tokens([a], "@a")

    # one token supplies whitespace - simple join
    self.__test_join_tokens(["x", "\ty"], "x\ty")
    self.__test_join_tokens(["x\t", "y"], "x\ty")
    self.__test_join_tokens([a, "\tx"], "@a\tx")
    self.__test_join_tokens(["x\t", a], "x\t@a")

    # no whitespace between tokens - space inserted
    self.__test_join_tokens([a, "x"], "@a x")
    self.__test_join_tokens(["x", a], "x @a")
    self.__test_join_tokens(["x", "y"], "x y")
    self.__test_join_tokens([a, b], "@a @b")

    # both tokens supply whitespace - drop second
    self.__test_join_tokens(["x ", "\ty"], "x y")
    self.__test_join_tokens(["x\t", " y"], "x\ty")

    # three tokens
    self.__test_join_tokens(["x", "\t", "y"], "x\ty")
    self.__test_join_tokens(["x\t", " ", " y"], "x\ty")
    self.__test_join_tokens([a, "\t", b], "@a\t@b")

  def __test_join_tokens(self, tokens, expected):
    result = Tag.join_tokens(tokens)
    self.assertEqual(expected, result, msg = "Expected Tag.join_tokens(%s) to equal '%s'" % (tokens, expected))

  def test_sort_edge_tags(self):
    c = ContextTag("c")
    p = ProjectTag("p")
    kv = KeyValueTag("k", "v")

    # trivial cases
    self.__test_sort_edge_tags([], [], trailing = True)
    self.__test_sort_edge_tags([], [], trailing = False)
    self.__test_sort_edge_tags(["x"], ["x"], trailing = True)
    self.__test_sort_edge_tags(["x"], ["x"], trailing = False)

    # no string tokens
    self.__test_sort_edge_tags([c], [c], trailing = True)
    self.__test_sort_edge_tags([c], [c], trailing = False)

    # correct sort order
    self.__test_sort_edge_tags([p, kv, c], [c, p, kv], trailing = True)
    self.__test_sort_edge_tags([p, kv, c], [c, p, kv], trailing = False)

    # sorts at correct end
    self.__test_sort_edge_tags([p, c, "x", p, c], [c, p, "x", p, c], trailing = False)
    self.__test_sort_edge_tags([p, c, "x", p, c], [p, c, "x", c, p], trailing = True)

    # sorts to first non-whitespace token
    self.__test_sort_edge_tags([p, " ", c, "x"], [c, p, "x"], trailing = False)
    self.__test_sort_edge_tags(["x", p, " ", c], ["x", c, p], trailing = True)

  def __test_sort_edge_tags(self, tokens, expected, trailing):
    result = Tag.sort_edge_tags(tokens, trailing)
    self.assertEqual(expected, result, msg = "Expected Tag.sort_edge_tags(%s) to equal '%s'" % (tokens, expected))


class AbstractSliceTest:
  action_name = "slice"

  def run_test(
      self,
      slice_args = [],
      expect_clean_exit = True,
      expect_warnings = False,
      todo0 = None,
      edit0 = None,
      edit1 = None,
      todo1 = None,
      strip_edit0_comments = True,
      export = {},
      unset = set()
      ):

    args = ["dummy.py"]

    args.append(self.action_name)
    args.append(self.slice_name)
    args.extend(slice_args)

    export_with_defaults = self.export.copy()
    export_with_defaults.update(export),

    env = VirtualTodoEnv(
        expect_clean_exit = expect_clean_exit,
        todo0 = todo0,
        edit0 = edit0,
        edit1 = edit1 if edit1 is not None else edit0,
        todo1 = todo1 if todo1 is not None else todo0,
        strip_edit0_comments = strip_edit0_comments,
        export = export_with_defaults,
        unset = unset
        )

    with capture(logging.getLogger("slice"), logging.WARN) as warnings:

      if expect_clean_exit:
        slice.main(env, args)
      else:
        with self.assertRaises(SystemExit):
          slice.main(env, args)

      have_warnings = len(warnings) > 0
      if expect_warnings:
        self.assertTrue(have_warnings, "Expected warnings")
      else:
        self.assertFalse(have_warnings, msg = "Expected no warnings: %s" % [w.getMessage() for w in warnings])

    env.assert_success()


  # the tests in this class should work with any slice as the todo file either starts empty, or causes a fatal error

  def test_editor_required(self):
    self.run_test(
        todo0 = [],
        edit0 = [],
        unset = {"EDITOR"},
        expect_warnings = True,
        expect_clean_exit = False
        )

  def test_no_tasks(self):
    self.run_test(
        todo0 = [],
        edit0 = []
        )

  def test_insert_task(self):
    self.run_test(
        todo0 = [],
        edit0 = [],
        edit1 = ["x"],
        todo1 = ["x"],
        )

  def test_insert_task_with_date(self):
    self.run_test(
        todo0 = [],
        edit0 = [],
        edit1 = ["x"],
        todo1 = ["2000-01-01 x"],
        export = {"TODOTXT_DATE_ON_ADD": "1"}
        )

  def test_refuse_to_edit_if_existing_task_looks_like_comment(self):
    self.run_test(
        todo0 = ["# x"],
        expect_warnings = True,
        expect_clean_exit = False
        )

  def test_ignore_comments_in_edit(self):
    self.run_test(
        todo0 = [],
        edit0 = [],
        edit1 = ["# x"],
        todo1 = [],
        )

  def test_leading_tag_order_normalized(self):
    self.run_test(
        todo0 = [],
        edit0 = [],
        edit1 = ["k:v +p @c x"],
        todo1 = ["@c +p k:v x"],
        )

  def test_trailing_tag_order_normalized(self):
    self.run_test(
        todo0 = [],
        edit0 = [],
        edit1 = ["x +p @c k:v"],
        todo1 = ["x @c +p k:v"],
        )

  def test_intermediate_tag_order_not_normalized(self):
    self.run_test(
        todo0 = [],
        edit0 = [],
        edit1 = ["x +p @c k:v y"],
        todo1 = ["x +p @c k:v y"],
        )

  def test_duplicate_contexts_normalized(self):
    self.run_test(
        todo0 = [],
        edit0 = [],
        edit1 = ["x @c @c"],
        todo1 = ["x @c"],
        expect_warnings = True
        )

  def test_duplicate_projects_normalized(self):
    self.run_test(
        todo0 = [],
        edit0 = [],
        edit1 = ["x +p +p"],
        todo1 = ["x +p"],
        expect_warnings = True
        )

  def test_duplicate_key_value_tags_normalized(self):
    self.run_test(
        todo0 = [],
        edit0 = [],
        edit1 = ["x k:v1 k:v1"],
        todo1 = ["x k:v1"],
        expect_warnings = True
        )

  def test_conflicting_key_value_tags_normalized(self):
    self.run_test(
        todo0 = [],
        edit0 = [],
        edit1 = ["x k:v1 k:v2"],
        todo1 = ["x k:v1"],
        expect_warnings = True
        )

  def test_redundant_start_date_normalized(self):
    self.run_test(
        todo0 = [],
        edit0 = [],
        edit1 = ["past t:1999-12-31", "present t:2000-01-01", "future t:2000-01-02"],
        todo1 = ["past", "present", "future t:2000-01-02"],
        )

  def test_completed_with_priority_normalized(self):
    self.run_test(
        todo0 = [],
        edit0 = [],
        edit1 = ["x 2000-01-01 (A) complete"],
        todo1 = ["x 2000-01-01 complete"]
        )

  # regression test
  def test_explicit_no_level_normalized(self):
    self.run_test(
        todo0 = [],
        edit0 = [],
        edit1 = ["(_) new"],
        todo1 = ["new"]
        )

  def test_unknown_id_tag_ignored(self):
    self.run_test(
        todo0 = [],
        edit0 = [],
        edit1 = ["i:42 x"],
        todo1 = ["x"],
        expect_warnings = True
        )

  # regression test
  def test_invalid_id_tag_ignored(self):
    self.run_test(
        todo0 = [],
        edit0 = [],
        edit1 = ["i:foo x"],
        todo1 = ["x"],
        expect_warnings = True
        )


class AbstractSliceAllTest(AbstractSliceTest):
  def test_comment_header(self):
    self.run_test(
        todo0 = [],
        edit0 = ["# All tasks", ""],
        edit1 = [],
        todo1 = [],
        strip_edit0_comments = False
        )

  def test_single_task(self):
    self.run_test(
        todo0 = ["task"],
        edit0 = ["i:1 task"]
        )

  def test_tasks_sorted(self):
    self.run_test(
        todo0 = ["(C) c", "(B) b", "(A) a"],
        edit0 = ["(A) i:3 a", "(B) i:2 b", "(C) i:1 c"]
        )

  def test_completed_tasks_hidden(self):
    self.run_test(
        todo0 = ["x 2000-01-01 done"],
        edit0 = []
        )

  def test_completed_tasks_not_hidden(self):
    self.run_test(
        todo0 = ["x 2000-01-01 done"],
        edit0 = ["x 2000-01-01 i:1 done"],
        export = {"TODOTXT_DISABLE_FILTER": "1"}
        )

  def test_future_tasks_hidden(self):
    self.run_test(
        todo0 = ["past t:1999-12-31", "present t:2000-01-01", "future t:2000-01-02"],
        edit0 = ["i:1 past t:1999-12-31", "i:2 present t:2000-01-01"]
        )

  def test_future_tasks_not_hidden(self):
    self.run_test(
        todo0 = ["past t:1999-12-31", "present t:2000-01-01", "future t:2000-01-02"],
        edit0 = ["i:1 past t:1999-12-31", "i:2 present t:2000-01-01", "i:3 future t:2000-01-02"],
        export = {"TODOTXT_DISABLE_FILTER": "1"}
        )

  def test_remove_task(self):
    self.run_test(
        todo0 = ["x"],
        edit0 = ["i:1 x"],
        edit1 = [],
        todo1 = [],
        )

  def test_edit_task(self):
    self.run_test(
        todo0 = ["a", "b"],
        edit0 = ["i:1 a", "i:2 b"],
        edit1 = ["i:1 x", "i:2 b"],
        todo1 = ["x", "b"],
        )

  def test_empty_line_preserved(self):
    self.run_test(
        todo0 = ["", "orig"],
        edit0 = ["i:2 orig"],
        edit1 = ["i:2 orig"],
        todo1 = ["", "orig"]
        )

  def test_empty_line_unchanged_if_no_other_edits(self):
    self.run_test(
        todo0 = ["", "orig"],
        edit0 = ["i:2 orig"],
        edit1 = ["i:2 orig"],
        todo1 = ["", "orig"],
        export = {"TODOTXT_PRESERVE_LINE_NUMBERS": "0"}
        )

  def test_empty_line_not_preserved_when_other_edits(self):
    self.run_test(
        todo0 = ["", "orig"],
        edit0 = ["i:2 orig"],
        edit1 = ["i:2 changed"],
        todo1 = ["changed"],
        export = {"TODOTXT_PRESERVE_LINE_NUMBERS": "0"}
        )

  # regression test
  def test_insert_task_empty_line_preserved(self):
    self.run_test(
        todo0 = ["", "orig"],
        edit0 = ["i:2 orig"],
        edit1 = ["i:2 orig", "new"],
        todo1 = ["", "orig", "new"]
        )

  # regression test
  def test_insert_task_empty_line_not_preserved(self):
    self.run_test(
        todo0 = ["", "orig"],
        edit0 = ["i:2 orig"],
        edit1 = ["i:2 orig", "new"],
        todo1 = ["orig", "new"],
        export = {"TODOTXT_PRESERVE_LINE_NUMBERS": "0"}
        )

  def test_leading_tag_order_not_normalized_if_no_other_edits(self):
    self.run_test(
        todo0 = ["k:v +p @c x"],
        edit0 = ["i:1 k:v +p @c x"],
        )

  def test_leading_tag_order_normalized_if_other_edits(self):
    self.run_test(
        todo0 = ["k:v +p @c x"],
        edit0 = ["i:1 k:v +p @c x"],
        edit1 = ["i:1 k:v +p @c y"],
        todo1 = ["@c +p k:v y"],
        )

  def test_trailing_tag_order_not_normalized_if_no_other_edits(self):
    self.run_test(
        todo0 = ["x k:v +p @c"],
        edit0 = ["i:1 x k:v +p @c"],
        )

  def test_trailing_tag_order_normalized_if_other_edits(self):
    self.run_test(
        todo0 = ["x k:v +p @c"],
        edit0 = ["i:1 x k:v +p @c"],
        edit1 = ["i:1 y k:v +p @c"],
        todo1 = ["y @c +p k:v"],
        )

  # regression test
  def test_url_is_not_considered_tag(self):
    self.run_test(
        todo0 = ["http://example.com @c"],
        edit0 = ["i:1 http://example.com @c"]
        )

  def test_duplicate_id_tag_ignored(self):
    self.run_test(
        todo0 = ["a"],
        edit0 = ["i:1 a"],
        edit1 = ["i:1 i:1 x"],
        todo1 = ["x"],
        expect_warnings = True
        )


class SliceListTest(AbstractSliceAllTest, unittest.TestCase):
  slice_name = "list"
  export = {}

  def test_comment_header_terms(self):
    self.run_test(
        slice_args = ["x", "y"],
        todo0 = [],
        edit0 = ["# Tasks containing terms: x y", ""],
        edit1 = [],
        todo1 = [],
        strip_edit0_comments = False
        )

  def test_list_task_with_term(self):
    self.run_test(
        slice_args = ["x"],
        todo0 = ["x", "y"],
        edit0 = ["i:1 x"]
        )

  def test_list_task_with_multiple_terms(self):
    self.run_test(
        slice_args = ["x", "y1"],
        todo0 = ["x y1", "y1 x", "x y2"],
        edit0 = ["i:1 x y1", "i:2 y1 x"]
        )

  def test_list_task_with_tag_does_not_strip_tag(self):
    self.run_test(
        slice_args = ["@c"],
        todo0 = ["x", "a @c"],
        edit0 = ["i:2 a @c"]
        )

  def test_list_task_hides_but_preserves_date(self):
    self.run_test(
        slice_args = [],
        todo0 = ["(A) 1999-12-31 a"],
        edit0 = ["(A) i:1 a"]
        )


class SliceMatchTest(AbstractSliceAllTest, unittest.TestCase):
  slice_name = "match"
  export = {}

  def test_comment_header_priority(self):
    self.run_test(
        slice_args = ["A"],
        todo0 = [],
        edit0 = ["# Tasks with priority (A)", ""],
        edit1 = [],
        todo1 = [],
        strip_edit0_comments = False
        )

  # regression test
  def test_comment_header_no_level_priority(self):
    self.run_test(
        slice_args = ["_"],
        todo0 = [],
        edit0 = ["# Tasks with priority (_)", ""],
        edit1 = [],
        todo1 = [],
        strip_edit0_comments = False
        )

  def test_comment_header_tags(self):
    self.run_test(
        slice_args = ["@c"],
        todo0 = [],
        edit0 = ["# Tasks with tags matching: @c", ""],
        edit1 = [],
        todo1 = [],
        strip_edit0_comments = False
        )

  def test_comment_header_priority_and_tags(self):
    self.run_test(
        slice_args = ["A", "@c"],
        todo0 = [],
        edit0 = ["# Tasks with priority (A) and tags matching: @c", ""],
        edit1 = [],
        todo1 = [],
        strip_edit0_comments = False
        )

  def test_match_task_with_priority(self):
    self.run_test(
        slice_args = ["A"],
        todo0 = ["x", "(A) a"],
        edit0 = ["i:2 a"]
        )

  def test_match_task_with_no_level_priority(self):
    self.run_test(
        slice_args = ["_"],
        todo0 = ["x", "(A) a"],
        edit0 = ["i:1 x"]
        )

  def test_match_task_with_context(self):
    self.run_test(
        slice_args = ["@c"],
        todo0 = ["x", "a @c"],
        edit0 = ["i:2 a"]
        )

  def test_match_task_with_project(self):
    self.run_test(
        slice_args = ["+p"],
        todo0 = ["x", "a +p"],
        edit0 = ["i:2 a"]
        )

  def test_match_task_with_kv(self):
    self.run_test(
        slice_args = ["k:v"],
        todo0 = ["x", "a k:v"],
        edit0 = ["i:2 a"]
        )

  def test_match_task_hides_but_preserves_date(self):
    self.run_test(
        slice_args = ["A"],
        todo0 = ["(A) 1999-12-31 a"],
        edit0 = ["i:1 a"]
        )

  def test_forged_id_tag_ignored(self):
    self.run_test(
        slice_args = ["A"],
        todo0 = ["(B) b"],
        edit0 = [],
        edit1 = ["i:1 a"],
        todo1 = ["(B) b", "(A) a"],
        expect_warnings = True
        )

  def test_insert_task_with_no_level_priority(self):
    self.run_test(
        slice_args = ["_"],
        todo0 = [],
        edit0 = [],
        edit1 = ["y"],
        todo1 = ["y"]
        )

  def test_insert_task_with_duplicate_tag(self):
    self.run_test(
        slice_args = ["@c"],
        todo0 = [],
        edit0 = [],
        edit1 = ["y @c"],
        todo1 = ["y @c"]
        )

  def test_insert_task_with_multiple_tags(self):
    self.run_test(
        slice_args = ["A", "@c", "+p", "k:v"],
        todo0 = [],
        edit0 = [],
        edit1 = ["y"],
        todo1 = ["(A) y @c +p k:v"]
        )

  def test_edit_task_with_multiple_tags(self):
    self.run_test(
        slice_args = ["A", "@c", "+p", "k:v"],
        todo0 = ["x", "(A) a @c +p k:v", "(A) a +q"],
        edit0 = ["i:2 a"],
        edit1 = ["i:2 y"],
        todo1 = ["x", "(A) y @c +p k:v", "(A) a +q"]
        )


class SliceReviewTest(AbstractSliceTest, unittest.TestCase):
  slice_name = "review"
  export = {"TODOTXT_SLICE_REVIEW_INTERVALS": ""}

  def test_comment_header(self):
    self.run_test(
        todo0 = [],
        edit0 = ["# Reviewable tasks (A:1)", ""],
        edit1 = [],
        todo1 = [],
        export = {"TODOTXT_SLICE_REVIEW_INTERVALS": "A:1"},
        strip_edit0_comments = False
        )

  def test_slice_review_intervals_required(self):
    self.run_test(
        todo0 = [],
        edit0 = [],
        unset = {"TODOTXT_SLICE_REVIEW_INTERVALS"},
        expect_warnings = True
        )

  def test_reviewable_by_age(self):
    self.run_test(
        todo0 = ["(A) 1999-12-31 a"],
        edit0 = ["(_) i:1 a"],
        export = {"TODOTXT_SLICE_REVIEW_INTERVALS": "A:1"},
        )

  def test_not_reviewable_by_age(self):
    self.run_test(
        todo0 = ["(A) 1999-12-31 a"],
        edit0 = [],
        export = {"TODOTXT_SLICE_REVIEW_INTERVALS": "A:2"},
        )

  def test_reviewable_by_priority(self):
    self.run_test(
        todo0 = ["(A) 2000-01-01 a", "(B) 2000-01-01 b"],
        edit0 = ["(_) i:1 a"],
        export = {"TODOTXT_SLICE_REVIEW_INTERVALS": "A:0,B:1"},
        )

  def test_reviewable_by_no_priority(self):
    self.run_test(
        todo0 = ["2000-01-01 a", "(B) 2000-01-01 b"],
        edit0 = ["(_) i:1 a"],
        export = {"TODOTXT_SLICE_REVIEW_INTERVALS": "_:0,B:1"},
        )

  def test_reviewable_by_unconfigured_priority(self):
    self.run_test(
        todo0 = ["(A) 2000-01-01 a", "(B) 2000-01-01 b"],
        edit0 = ["(_) i:2 b"],
        export = {"TODOTXT_SLICE_REVIEW_INTERVALS": "A:1"},
        )

  # regression test
  def test_reviewable_by_unconfigured_no_priority(self):
    self.run_test(
        todo0 = ["(A) 2000-01-01 a", "2000-01-01 b"],
        edit0 = ["(_) i:2 b"],
        export = {"TODOTXT_SLICE_REVIEW_INTERVALS": "A:1"},
        )

  def test_reviewable_by_start_date(self):
    self.run_test(
        todo0 = ["1999-12-31 a t:2000-01-01", "1999-12-31 b t:2000-01-02"],
        edit0 = ["(_) i:1 a t:2000-01-01"],
        export = {"TODOTXT_SLICE_REVIEW_INTERVALS": "_:5"},
        )

  def test_set_complete_date_does_not_reset_create_date(self):
    self.run_test(
        todo0 = ["(A) 1999-12-31 a"],
        edit0 = ["(_) i:1 a"],
        edit1 = ["x 2000-01-01 (_) i:1 a"],
        todo1 = ["x 2000-01-01 1999-12-31 a"],
        export = {"TODOTXT_SLICE_REVIEW_INTERVALS": "A:1"},
        )

  def test_set_complete_date_clears_start_date(self):
    self.run_test(
        todo0 = ["1999-12-31 a t:2000-01-01"],
        edit0 = ["(_) i:1 a t:2000-01-01"],
        edit1 = ["x 2000-01-01 (_) i:1 a t:2000-01-01"],
        todo1 = ["x 2000-01-01 1999-12-31 a"],
        export = {"TODOTXT_SLICE_REVIEW_INTERVALS": "_:5"},
        )

  def test_set_start_date_resets_create_date(self):
    self.run_test(
        todo0 = ["(A) 1999-12-31 a"],
        edit0 = ["(_) i:1 a"],
        edit1 = ["(_) i:1 a t:2001-01-02"],
        todo1 = ["(A) 2000-01-01 a t:2001-01-02"],
        export = {"TODOTXT_SLICE_REVIEW_INTERVALS": "A:1"},
        )

  def test_set_start_date_does_not_clear_start_date(self):
    self.run_test(
        todo0 = ["1999-12-31 a t:2000-01-01"],
        edit0 = ["(_) i:1 a t:2000-01-01"],
        edit1 = ["(_) i:1 a t:2001-01-02"],
        todo1 = ["2000-01-01 a t:2001-01-02"],
        export = {"TODOTXT_SLICE_REVIEW_INTERVALS": "_:5"},
        )

  def test_set_priority_resets_create_date(self):
    self.run_test(
        todo0 = ["(A) 1999-12-31 a"],
        edit0 = ["(_) i:1 a"],
        edit1 = ["(B) i:1 a"],
        todo1 = ["(B) 2000-01-01 a"],
        export = {"TODOTXT_SLICE_REVIEW_INTERVALS": "A:1"},
        )

  def test_set_priority_clears_start_date(self):
    self.run_test(
        todo0 = ["1999-12-31 a t:2000-01-01"],
        edit0 = ["(_) i:1 a t:2000-01-01"],
        edit1 = ["(B) i:1 a t:2000-01-01"],
        todo1 = ["(B) 2000-01-01 a"],
        export = {"TODOTXT_SLICE_REVIEW_INTERVALS": "_:5"},
        )

  def test_edits_preserved(self):
    self.run_test(
        todo0 = ["(A) 1999-12-31 a"],
        edit0 = ["(_) i:1 a"],
        edit1 = ["(_) i:1 b"],
        todo1 = ["(A) 1999-12-31 b"],
        export = {"TODOTXT_SLICE_REVIEW_INTERVALS": "A:1"},
        )

  # regression test
  def test_insert_hidden(self):
    self.run_test(
        todo0 = [],
        edit0 = [],
        edit1 = ["a t:2000-01-02"],
        todo1 = ["a t:2000-01-02"],
        export = {"TODOTXT_DATE_ON_ADD": "0"}
        )

  # regression test
  def test_insert_hidden_with_date(self):
    self.run_test(
        todo0 = [],
        edit0 = [],
        edit1 = ["a t:2000-01-02"],
        todo1 = ["2000-01-01 a t:2000-01-02"],
        export = {"TODOTXT_DATE_ON_ADD": "1"}
        )


class SliceFutureTest(AbstractSliceTest, unittest.TestCase):
  slice_name = "future"
  export = {}

  def test_comment_header(self):
    self.run_test(
        todo0 = [],
        edit0 = ["# Future tasks", ""],
        edit1 = [],
        todo1 = [],
        strip_edit0_comments = False
        )

  def test_future_start_date(self):
    self.run_test(
        todo0 = ["future t:2000-01-02"],
        edit0 = ["i:1 future t:2000-01-02"]
        )

  def test_past_or_present_start_dates_hidden(self):
    self.run_test(
        todo0 = ["past t:1999-12-31", "present t:2000-01-01"],
        edit0 = []
        )

  def test_normal_hidden(self):
    self.run_test(
        todo0 = ["normal"],
        edit0 = []
        )

  def test_completed_hidden(self):
    self.run_test(
        todo0 = ["x 2000-01-01 completed"],
        edit0 = []
        )

  # regression test
  def test_completed_future_start_date_hidden(self):
    self.run_test(
        todo0 = ["x 2000-01-01 completed t:2000-01-02"],
        edit0 = []
        )

  # regression test
  def test_completed_future_start_date_not_hidden(self):
    self.run_test(
        todo0 = ["x 2000-01-01 completed t:2000-01-02"],
        edit0 = ["x 2000-01-01 i:1 completed t:2000-01-02"],
        export = {"TODOTXT_DISABLE_FILTER": "1"}
        )

  def test_sorted_by_start_date(self):
    self.run_test(
        todo0 = ["(A) a t:2000-01-04", "(C) c t:2000-01-03", "(B) b t:2000-01-02"],
        edit0 = ["(B) i:3 b t:2000-01-02", "(C) i:2 c t:2000-01-03", "(A) i:1 a t:2000-01-04"]
        )


if __name__ == "__main__":
  unittest.main()

