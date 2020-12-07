from watchdog.utils.dirsnapshot import DirectorySnapshot, DirectorySnapshotDiff
import os
from analog.bin.logger.logger import Logger
from threading import Thread, Event
from queue import Queue


class ConsecutiveThread(Thread):
    def __init__(self, stop_event, func, args=None, kwargs=None, interval=5, daemon=True):
        Thread.__init__(self, daemon=daemon)
        self.stopped = stop_event
        self.func = func
        self.args = args if args is not None else tuple()
        self.kwargs = kwargs if kwargs is not None else dict()
        self.interval = interval

    def run(self):
        while not self.stopped.wait(self.interval):
            self.func(*self.args, **self.kwargs)

    def stop(self):
        self.stopped.set()

    def clear(self):
        self.stopped.clear()


class FileSupervisor:

    def __init__(self, _path, _queue: Queue, interval=5, recursive=True, daemon=True, log_path=None, log_name=None):
        """
        文件监视类
        :param _path: 要监视的目录
        :param interval: 时间间隔，即每interval检查一次变更
        :param recursive: 是否递归监视
        :param daemon: 守护线程
        """
        super().__init__()
        self.path = _path
        self.interval = interval
        self.snap = DirectorySnapshot(self.path, recursive=recursive)
        self.daemon = daemon
        self.stop_flag = Event()
        self.logger = None
        self.queue = _queue
        self.thread = ConsecutiveThread(self.stop_flag, self.get_diff, daemon=True)

        if log_path:
            self.log_name = log_name if log_name is not None else "FileSupervisor-%08x" % (
                int.from_bytes(os.urandom(4), byteorder='big'))
            self.log_path = log_path
            self.logger = Logger(self.log_name, self.log_path)
            self.logger.register_log_function("modify", "MODIFY")
            self.logger.register_log_function("create", "CREATE")

    def start(self):
        self.thread.start()

    def get_diff(self):
        current_snap = DirectorySnapshot(self.path)
        diff = DirectorySnapshotDiff(self.snap, current_snap)
        self.snap = current_snap
        if len(diff.files_modified) != 0:
            self.logger.modify(str(diff.files_modified))
        if len(diff.files_created) != 0:
            self.logger.create(str(diff.files_created))

        changes = diff.files_modified + diff.files_created
        if len(changes) != 0:
            self.queue.put(changes)

    def stop(self):
        self.thread.stop()

    def clear_flag(self):
        self.thread.clear()


if __name__ == "__main__":
    pass
