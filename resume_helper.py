import xbmc
import xbmcgui
import json
import os

# HISTORY_PATH will be defined inside the method to avoid early xbmc.translatePath call issues.

class KodicekPlayer(xbmc.Player):
    def __init__(self):
        super(KodicekPlayer, self).__init__()
        self.current_file = None

    def onPlayBackStarted(self):
        self.current_file = self.getPlayingFile()
        
    def onPlayBackStopped(self):
        self.save_resume_time()

    def onPlayBackEnded(self):
        self.save_resume_time(finished=True)

    def save_resume_time(self, finished=False):
        if not self.current_file:
            xbmc.log("KodicekPlayer (resume_helper): No current_file, cannot save resume time.", xbmc.LOGDEBUG)
            return
        
        current_pos_float = self.getTime()
        current_pos_int = int(current_pos_float)
        xbmc.log(f"KodicekPlayer (resume_helper): save_resume_time. current_file: '{self.current_file}', current_pos_float: {current_pos_float}, current_pos_int: {current_pos_int}, finished: {finished}", xbmc.LOGINFO)
        
        HISTORY_PATH = xbmc.translatePath('special://profile/addon_data/plugin.video.kodicek/history.json')
        
        try:
            if os.path.exists(HISTORY_PATH):
                with open(HISTORY_PATH, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            else:
                history = []
            
            # Ensure history is a list
            if not isinstance(history, list):
                xbmc.log(f"Kodicek resume save error: History is not a list. Found: {type(history)}", xbmc.LOGERROR)
                history = []

            item_found = False
            for item in history:
                if isinstance(item, dict) and item.get("file_path") == self.current_file:
                    if finished:
                        item.pop("resume_time", None)
                        item["finished"] = True 
                        xbmc.log(f"KodicekPlayer (resume_helper): Marked as finished and removed resume_time for: {self.current_file}", xbmc.LOGINFO)
                    else:
                        item["resume_time"] = current_pos_int # Use the already fetched int value
                        item.pop("finished", None)
                        xbmc.log(f"KodicekPlayer (resume_helper): Saved resume_time {current_pos_int} for: {self.current_file}", xbmc.LOGINFO)
                    item_found = True
                    break
            
            # If item not found, and we are saving (not finishing), it implies a new playback not yet in history.
            # This case should ideally be handled when the item is first added to history.
            # However, if current_file is playing and not in history, this logic won't update/add it.
            # The current design assumes the item is already in history when playback starts.

            with open(HISTORY_PATH, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            xbmc.log(f"Kodicek resume save error: {e}", xbmc.LOGERROR)
