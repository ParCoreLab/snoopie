import streamlit as st
from .tables import *
from copy import deepcopy
from .streamlit_globals import setup_globals
import os
import pickle
from io import TextIOWrapper
from typing import List, Dict, Tuple

tables = {}

current_table = None

_counter = 0
_table_keys = []
_devices = set()
_pid = -1


def change_table(line: str):
    global current_table, _table_keys
    for key in tables.keys():
        if line.startswith(tables[key]["starts_with"]):
            current_table = key
            _table_keys = line.strip().split(",")
            return True
    return False


def parse_line(line: str, gbs: tuple):
    global _counter

    _counter += 1
    if _counter % 100000 == 0:
        print("reading data, line:", _counter)

    if current_table == None:
        change_table(line)
    else:
        tables[current_table]["parser"](line, gbs)


def isInt_try(v):
    try:
        i = int(v)
    except:
        return False
    return True


def parse_codeline_info(line: str, gbs: tuple):
    _, ops = gbs
    if change_table(line):
        return
    if current_table != "codeline_info":
        return
    data = {}
    data["pid"] = _pid
    vals = line.strip().split(",")  # change this later
    for index in range(len(_table_keys)):
        if isInt_try(vals[index]):
            data[_table_keys[index].strip()] = int(vals[index])
        else:
            data[_table_keys[index].strip()] = vals[index]

    CodeLineInfoRow(**data)


def parse_obj_info(line: str, gbs: tuple):
    _, ops = gbs
    if change_table(line):
        return
    if current_table != "obj_info":
        return
    data = {}
    data["pid"] = _pid
    vals = line.strip().split(",")  # change this later
    for index in range(len(_table_keys)):
        if isInt_try(vals[index]):
            data[_table_keys[index].strip()] = int(vals[index])
        else:
            data[_table_keys[index].strip()] = vals[index]

    ObjNameRow(**data)


def parse_context_info(line: str, gbs: tuple):
    _, ops = gbs
    if change_table(line):
        return
    if current_table != "context_info":
        return
    data = {}
    data["pid"] = _pid
    vals = line.strip().split(",")  # change this later
    for index in range(len(_table_keys)):
        if isInt_try(vals[index]):
            data[_table_keys[index].strip()] = int(vals[index])
        else:
            data[_table_keys[index].strip()] = vals[index]

    ContextRow(**data)


def parse_offset_info(line: str, gbs: tuple):
    _, ops = gbs
    if change_table(line):
        return
    if current_table != "offset_info":
        return
    data = {}
    data["pid"] = _pid
    vals = line.strip().split(",")  # change this later
    for index in range(len(_table_keys)):
        if isInt_try(vals[index]):
            data[_table_keys[index].strip()] = int(vals[index])
        else:
            data[_table_keys[index].strip()] = vals[index]

    _devices.add(data["dev_id"])
    ObjIdRow(**data)


def parse_func_info(line: str, gbs: tuple):
    _, ops = gbs
    if change_table(line):
        return
    if current_table != "func_info":
        return
    data = {}

    # since function name contains "," we need to be careful
    # assume filepath does not contain ","

    sep = [-1, -1, -1]
    sep[0] = line.find(",", 0)
    while True:
        i1 = line.find(",", max(sep[1], sep[0]) + 1)
        if i1 == -1:
            break
        i2 = line.find(",", i1 + 1)
        if i2 == -1:
            # sep[1] = sep[2]
            # sep[2] = i1
            break
        sep[1] = i1
        sep[2] = i2
    split_data = (
        line[: sep[0]].strip(),
        line[sep[0] + 1 : sep[1]].strip(),
        line[sep[1] + 1 : sep[2]].strip(),
        line[sep[2] + 1 :].strip(),
    )
    FunctionInfoRow(
        _pid, int(split_data[0]), split_data[1], split_data[2], int(split_data[3])
    )


def parse_site_info(line: str, gbs: tuple):
    _, ops = gbs
    if change_table(line):
        return
    if current_table != "site_info":
        return
    split_data = line.strip().split(",")  # change this later
    SiteInfoRow(
        _pid, int(split_data[0]), split_data[1], int(split_data[2])
    )


def parse_op_info(line: str, gbs: tuple):
    _, ops = gbs
    if change_table(line):
        return
    if current_table != "op_info":
        return

    data = {}
    data["pid"] = _pid
    vals = line.strip().split(",")  # change this later
    for index in range(len(_table_keys)):
        if isInt_try(vals[index]):
            data[_table_keys[index].strip()] = int(vals[index])
        else:
            data[_table_keys[index].strip()] = vals[index]

    address = data["addr"]
    obj_offset = data["obj_offset"]
    operation = data["op_code"]
    line_index = data["code_line_index"]
    mem_range = data.get("mem_range", 4)

    if "U8" in operation:
        mem_range = 4
    if "U16" in operation:
        mem_range = 8
    elif "32" in operation:
        mem_range = 4
    elif "64" in operation:
        mem_range = 8
    elif "128" in operation:
        mem_range = 16
    # print("OPREAD  " + operation)
    ops.add(operation)
    new_row = OpInfoRow(**data)
    _devices.add(data["running_dev_id"])
    _devices.add(data["mem_dev_id"])

    # device = "GPU" + str(data["running_dev_id"])
    # owner = "GPU" + str(data["mem_dev_id"])
    # pair = device + "-" + owner


tables = {
    "op_info": {"starts_with": "op_code", "parser": parse_op_info}, # main log
    "func_info": {"starts_with": "pc", "parser": parse_func_info}, # mem_alloc_site_log
    "offset_info": {"starts_with": "offset", "parser": parse_offset_info}, # address_range_log
    "obj_info": {"starts_with": "obj_id", "parser": parse_obj_info}, # data_object_log
    "context_info": {"starts_with": "context_id", "parser": parse_context_info}, # exec_context_log
    "site_info": {"starts_with": "site_id", "parser": parse_site_info}, # exec_site_log
    "codeline_info": {"starts_with": "code_line_index", "parser": parse_codeline_info}, # codeline_log
}


def get_pid(filename: str) -> int:
    if filename.endswith(".txt"):
        # one of address_range_log_pid.txt, codeline_log_pid.txt, data_object_log_pid.txt, mem_alloc_site_log_pid.txt
        beforepid = filename.rfind("_")
        slice = filename[beforepid + 1 : -4]
        if not slice.isdigit():
            return -1
        return int(slice)
    else:
        # snoopie-log-pid or snoopie-log-pid.zstd
        last = -4 if filename.endswith(".zst") else -1
        beforepid = filename.rfind("_")
        slice = filename[beforepid + 1 : last]
        if not slice.isdigit():
            return -1
        return int(slice)


# @st.cache_data
def read_data(
    file: TextIOWrapper | List[TextIOWrapper], filename: str | List[str], gbs
):
    global _pid
    if file == None or filename == None:
        st.experimental_rerun()  # this shouldn't be here need to fix the problem soon

    all_pids = []

    devices, ops = gbs

    # prints all files
    graph_name = ""
    pickle_file = None
    pickle_filename = ""

    for i in range(len(filename)):
        filename[i] = filename[i].split("/")[-1]
    print(file, filename)

    if isinstance(filename, list):
        all_pids = [get_pid(i) for i in filename]
        all_pids.sort()
        pickle_filename = "-".join([str(i) for i in all_pids]) + ".pkl"
    else:
        pickle_filename = "".join(filename.split(".")[:-1]) + ".pkl"

    st.session_state.pickle_filename = pickle_filename

    if os.path.isfile(pickle_filename):
        with open(pickle_filename, "rb") as f:
            pickle_file = pickle.load(f)
            # if len(pickle_file) > 6:
            #     new_pickle_file = pickle_file[:5]
            #     new_pickle_file.append(pickle_file[6])
            #     pickle_file = new_pickle_file
            for item in pickle_file:
                pass
                # print(item)
                # print()
            print("Data loaded from " + pickle_filename)

    reading_data = 0
    opkeys = []
    objkeys = []
    counter = 0

    if pickle_file is None:
        if isinstance(file, list):
            for f, fn in zip(file, filename):
                _pid = get_pid(fn)
                for line in f:
                    parse_line(line, gbs)
        else:
            # TODO: Check if we need get pid in teh case of a single file?
            for line in file:
                parse_line(line, gbs)
        CodeLineInfoRow.inferred_home_dir = CodeLineInfoRow.infer_home_dir(
            CodeLineInfoRow.table()
        )
        # print("INFERRED dir " + CodeLineInfoRow.inferred_home_dir)
        # if (CodeLineInfoRow.inferred_home_dir == ""):
        #     SiteInfoRow.inferred_home_dir = SiteInfoRow.infer_home_dir(
        #     SiteInfoRow.table())
        ts = set()
        # print("INFERRED dir " + SiteInfoRow.inferred_home_dir)
        for op in OpInfoRow._table:
            id, name = op.get_obj_info()
            u: UniqueObject = op.get_unique_obj()
            if u is None:
                continue
            if u not in SnoopieObject.all_objects:
                tmp = SnoopieObject(name.var_name, id.obj_id, name.call_stack)
                SnoopieObject.all_objects[u] = tmp
            so: SnoopieObject = SnoopieObject.all_objects[u]
            so.add_op(op)
            so.add_addres_range(id)
            op.related_object = so

        tempdev = deepcopy(_devices)
        if -1 in tempdev:
            tempdev.remove(-1)
        print(tempdev)
        st.session_state.gpu_num = max(max(tempdev) + 1, len(tempdev))
        gpu_num = max(max(tempdev) + 1, len(tempdev))
        print("Reading complete")

        all_data = [
            OpInfoRow._table,
            SnoopieObject.all_objects,
            FunctionInfoRow.by_pc,
            ObjIdRow.by_dev_offset,
            ObjIdRow.by_pid_offset,
            ObjNameRow.by_obj_id,
            ContextRow.by_context_id,
            SiteInfoRow.by_pc,
            # SiteInfoRow.inferred_home_dir,
            CodeLineInfoRow.by_cd_index,
            CodeLineInfoRow.inferred_home_dir,
            gpu_num,
            ops,
        ]

        with open(pickle_filename, "wb") as pf:
            pickle.dump(all_data, pf)
            print("Data saved to " + pickle_filename)
    else:
        (
            OpInfoRow._table,
            SnoopieObject.all_objects,
            FunctionInfoRow.by_pc,
            ObjIdRow.by_dev_offset,
            ObjIdRow.by_pid_offset,
            ObjNameRow.by_obj_id,
            ContextRow.by_context_id,
            SiteInfoRow.by_pc,
            # SiteInfoRow.inferred_home_dir,
            CodeLineInfoRow.by_cd_index,
            CodeLineInfoRow.inferred_home_dir,
            gpu_num,
            ops,
        ) = pickle_file

        st.session_state.gpu_num = gpu_num

    return gpu_num, ops
