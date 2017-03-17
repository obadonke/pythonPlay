#!/usr/bin/env python3

import sys
import os.path
import json
from gatherperfdata import JSonLabels, OpLabels, TestLabels, TEST_SUITE_LABEL
import re

def treat_build_number(data, source_file):
    """Look for and correct build version missing."""
    build_tested = data[JSonLabels.BUILD_TESTED]
    if (build_tested[JSonLabels.REVISION] > 0
        and build_tested[JSonLabels.VERSION_SHORT] != ""):
        return

    REGEX = r"r([0-9]+).*?v([0-9.]+)"
    match = re.search(REGEX, source_file) 
    if match is None:
        print("Could not fix build num for: {}".format(source_file), sys.stderr)
        return

    rev = int(match.group(1))
    ver = match.group(2)
    build_tested[JSonLabels.REVISION] = rev
    build_tested[JSonLabels.VERSION_SHORT] = ver
    build_tested[JSonLabels.VERSION_LONG] = ver


def treat_suite_label(data):
    """Changes old TestComplete to the new label"""
    if data[JSonLabels.TEST_SUITE_LABEL] != "TestComplete":
        return

    data[JSonLabels.TEST_SUITE_LABEL] = TEST_SUITE_LABEL


def treat_op_structure(data):
    """This will convert old format duration/filesize to new."""
    test_results = data[JSonLabels.TEST_RESULTS]
    if len(test_results) == 0:
        return

    op_results  = test_results[0][JSonLabels.OP_RESULTS]
    if len(op_results) == 0:
        return

    return


def test_result_iter(data, label_sel_func):
    test_results = data[JSonLabels.TEST_RESULTS]
    for test_result in test_results:
        test_label = test_result[JSonLabels.LABEL]
        if label_sel_func(test_label):
            yield (test_label, test_result)


def treat_basic_avg_ops(data):
    """This will recalculate the averages in ms."""
    def calc_avg(test_res, op_name):
        total_duration = 0
        op_count = 0
        op_results = test_res[JSonLabels.OP_RESULTS]
        for op in op_results:
            op_label = op[JSonLabels.LABEL]
            if (not op_label.startswith(op_name)) or op_label.endswith("1"):
                continue

            op_count += 1
            if JSonLabels.DURATION in op:
                total_duration += op[JSonLabels.DURATION]
            else:
                total_duration += op[JSonLabels.VALUE]

        if op_count == 0:
            # can happen if the test failed
            return

        avg = int(total_duration/op_count)
        avg_label = "Average" + op_name

        # find average result and update it
        for op in op_results:
            op_label = op[JSonLabels.LABEL]
            if not op_label == avg_label:
                continue

            if JSonLabels.DURATION in op:
                op[JSonLabels.DURATION] = avg
            else:
                op[JSonLabels.VALUE] = avg

    def test_selector(label):
        return label == "DPT1" or label == "DPT2" or label == "BBT3"

    for (test_label, test_result) in test_result_iter(data, test_selector):
        if test_label == "BBT3":
            calc_avg(test_result, "Build")
        else:
            calc_avg(test_result, "Check")
            calc_avg(test_result, "Design")
    return


def treat_frame_ops(data):
    """This will fix all ops that say LayoutPaint when they should be FramePaint"""
    def test_selector(label):
        return label == TestLabels.SW_FORMWORK_TEST or label == TestLabels.UK_FBMT_TEST

    for (test_label, test_result) in test_result_iter(data, test_selector):
        op_results = test_result[JSonLabels.OP_RESULTS]
        for op in op_results:
            op_label = op[JSonLabels.LABEL]
            if op_label == "LayoutPaint":
                op[JSonLabels.LABEL] = OpLabels.FRAME_PAINT

            if op_label == "Refresh":
                op[JSonLabels.LABEL] = OpLabels.FRAME_REFRESH


def main(source_path, target_path):
    print("Converting files in {}. Output to {}".format(source_path, target_path))

    if not os.path.exists(source_path):
        print("Folder '{}' does not exist.".format(source_path))
        return

    if not os.path.exists(target_path):
        print("Folder '{}' does not exist.".format(target_path))
        return


    source_files = [name for name in os.listdir(source_path)
                   if os.path.isfile(os.path.join(source_path, name)) and name.endswith(".json")]

    for source_file in source_files:
        current_filepath = os.path.join(source_path, source_file)
        target_filepath = os.path.join(target_path, source_file)
        with open(current_filepath, 'r') as f:
            data = json.load(f)

        #treat_build_number(data, source_file)
        #treat_suite_label(data)
        #treat_op_structure(data)
        treat_basic_avg_ops(data)
        treat_frame_ops(data)

        with open(target_filepath, 'w') as f:
            json.dump(data, f, indent=3, sort_keys=True)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: {} <source_path> <target_path>".format(sys.argv[0]))
        exit()

    source_p = sys.argv[1] if sys.argv[1] != "-" else r"./jcv_test/legacy"
    target_p = sys.argv[2] if sys.argv[2] != "-" else r"./jcv_test/converted"

    main(source_p, target_p)
