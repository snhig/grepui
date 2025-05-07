from PySide6.QtCore import QObject, Signal, QRunnable, Slot

class SearchWorkerSignals(QObject):
    finished = Signal(list)
    error = Signal(str)

class SearchWorker(QRunnable):
    def __init__(self, root_path, extension, search_string, use_regex, recursive, case_insensitive, search_fn):
        super().__init__()
        self.root_path = root_path
        self.extension = extension
        self.search_string = search_string
        self.use_regex = use_regex
        self.recursive = recursive
        self.case_insensitive = case_insensitive
        self.search_fn = search_fn
        self.signals = SearchWorkerSignals()

    @Slot()
    def run(self):
        try:
            results = self.search_fn(
                self.root_path,
                self.extension,
                self.search_string,
                use_regex=self.use_regex,
                recursive=self.recursive,
                case_insensitive=self.case_insensitive
            )
            self.signals.finished.emit(results)
        except Exception as e:
            self.signals.error.emit(str(e))
