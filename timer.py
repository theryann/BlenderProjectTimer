bl_info = {
    "name": "Blender Project Timer",
    "author": "Darian Patzak",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "Info",
    "description": "Log and display time spend on Blender Projects in this directory",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Interface"
}

import bpy
import json
import time
import os

INACTIVE_TIMEOUT: int = 60 * 3      # 3 minutes before counted as inactive
CHECK_INTERVAL: int = 10            # 10 seconds between checking if still working

start_time_s: int = None            # start time in epoch seconds to begin counting from (resets after each inactivity)
curr_session_time_s: int = None     # the seconds spend working on the current project

SAVE_FILE_NAME: str = 'log.json'
blend_file_name: str = None

def save_working_time_to_json() -> None:
    """ load log file, add new elapsed time and save """
    log_file_path: str = os.join( os.getcwd(), SAVE_FILE_NAME )
    log_file: dict = None

    # create logfile if not existis
    if not os.path.exists( log_file_path ):
        with open( log_file_path, 'w' ) as fp:
            json.dump({
                "total_minutes": 0,
                "individual_files": {},
                "all_sessions": []
            },
            fp, indent=4)
    
    # load logfile
    with open( log_file_path, 'r' ) as fp:
        log_file = json.load( log_file_path )

    elapsed_time_s: int = start_time_s + curr_session_time_s
    begin_string: str = time.strftime('%FT%H:%M:%S', time.localtime( start_time_s ))
    end_string: str   = time.strftime('%FT%H:%M:%S', time.localtime( elapsed_time_s ))

    # add current session to list of all sessions
    log_file["all_sessions"].append({
        "file": blend_file_name,
        "starttime": begin_string,
        "endtime": end_string,
        "minutes_elapsed": elapsed_time_s
    })

    # add elapsed time to counter of this blend file
    # and sum all files to new total time

    if blend_file_name in log_file.get("individual_files"):
        log_file["individual_files"][blend_file_name] += elapsed_time_s
    else:
        log_file["individual_files"][blend_file_name]  = elapsed_time_s
    
    log_file["total_minutes"] = sum( log_file.get("individual_files").values() )
    
    # save updated file
    with open( log_file_path, 'w' ) as fp:
        json.dump( log_file, fp, indent=4 )


    


