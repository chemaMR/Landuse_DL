#!/usr/bin/env python
# Filename: parallel_predict_rts.py 
"""
introduction:

authors: Huang Lingcao
email:huanglingcao@gmail.com
add time: 24 September, 2019
"""

# note: it seems the codes cannot run on multi-nodes on ITSC services. So I have to submit jobs using different separately

import os, sys
import time

HOME = os.path.expanduser('~')
codes_dir2 = HOME +'/codes/PycharmProjects/DeeplabforRS'
sys.path.insert(0, codes_dir2)

import basic_src.basic as basic
import basic_src.io_function as io_function

basic.setlogfile('parallel_predict_rtsLog.txt')

predict_script = HOME + '/codes/PycharmProjects/Landuse_DL/sentinelScripts/predict_rts_oneImg.sh'

import GPUtil
import datetime

machine_name = os.uname()[1]

start_time = datetime.datetime.now()

# remove previous results
outdir = 'multi_inf_results'
if os.path.isdir(outdir) and 'chpc' not in machine_name:  # on ITSC service, need to manually deleted previous results
    io_function.delete_file_or_dir(outdir)

os.system('mkdir -p '+ outdir)

# get GPU information on the machine
# https://github.com/anderskm/gputil
# deviceIDs = GPUtil.getAvailable(order = 'first', limit = 100, maxLoad = 0.5,
#                                 maxMemory = 0.5, includeNan=False, excludeID=[], excludeUUID=[])
# print('available GPUs:',deviceIDs)


with open('inf_image_list.txt','r') as inf_obj:
    inf_img_list = [name.strip() for name in inf_obj.readlines()]

img_count = len(inf_img_list)
if img_count < 1:
    raise ValueError('No image in inf_image_list.txt')

def is_file_exist_in_folder(folder):
    file_list = io_function.get_file_list_by_pattern(folder, '*.*')
    if len(file_list) > 0:
        return True
    else:
        return False

# parallel inference images
idx = 0
while idx < img_count:

    # get available GPUs
    deviceIDs = GPUtil.getAvailable(order='first', limit=100, maxLoad=0.5,
                                    maxMemory=0.5, includeNan=False, excludeID=[], excludeUUID=[])
    basic.outputlogMessage('on ' + machine_name + ', available GPUs:'+str(deviceIDs))
    if len(deviceIDs) < 1:
        time.sleep(60)  # wait one minute, then check the available GPUs again
        continue

    # set only the first available visible
    gpuid = deviceIDs[0]

    # run inference
    save_dir = os.path.join(outdir,'I%d'%idx)
    inf_list_file = os.path.join(outdir,'%d.txt'%idx)

    # if it already exist, then skip
    if os.path.isdir(save_dir) and is_file_exist_in_folder(save_dir):
        continue

    with open(inf_list_file,'w') as inf_obj:
        inf_obj.writelines(inf_img_list[idx] + '\n')
    basic.outputlogMessage('%d: predict image %s on GPU %d of %s'%(idx, inf_img_list[idx], gpuid,machine_name))
    command_string = predict_script + ' ' + save_dir + ' ' + inf_list_file + ' ' + str(gpuid)
    # status, result = basic.exec_command_string(command_string)  # this will wait command finished
    # print(status, result)
    os.system(command_string + "&")

    idx += 1

    # wait until predicted image patches exist or exceed 20 minutes
    start_time = time.time()
    elapsed_time = time.time() - start_time
    while elapsed_time < 20*60:
        elapsed_time = time.time() - start_time
        file_exist = is_file_exist_in_folder(save_dir)
        if file_exist is True:
            break
        else:
            time.sleep(5)

    # if 'chpc' in machine_name:
    #     time.sleep(60)  # wait 60 second on ITSC services
    # else:
    #     time.sleep(10)


end_time = datetime.datetime.now()

diff_time = end_time - start_time
out_str = "%s: time cost of parallel inference: %d seconds"%(str(end_time),diff_time.seconds)
basic.outputlogMessage(out_str)
with open ("time_cost.txt",'a') as t_obj:
    t_obj.writelines(out_str+'\n')
