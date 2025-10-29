from collections import deque
from threading import Thread, Event, Lock
from time import sleep


class QueueItem:
    def __init__(self, data):
        self.data = data
        self.result = None
        self.done = Event()
    
    def wait(self):
        self.done.wait()
    
    def set_result(self, result):
        self.result = result
        self.done.set()
    
    def get_result(self):
        self.wait()
        return self.result

class CustomQueue[T]:
    def __init__(self):
        self.queue = deque()
        self.lock = Lock()
    
    def put(self, item: T):
        with self.lock:
            self.queue.append(item)
    
    def get(self) -> None | T:
        with self.lock:
            return self.queue.popleft() if self.queue else None

    def peek(self) -> None | T:
        with self.lock:
            return self.queue[0] if self.queue else None

    def count(self):
        with self.lock:
            return len(self.queue)


class QueueWorker(Thread):
    def __init__(self, func, items: list[QueueItem]):
        super().__init__(daemon=True)
        self.func = func
        self.items = items
        self.start()
    
    def run(self):
        datas = [item.data for item in self.items]
        print("[@] QueueWorker run", len(datas), list(map(len, datas)))
        results = self.func(datas)
        for item, result in zip(self.items, results):
            item.set_result(result)


class TaskQueue(Thread):
    # MAX_IMAGE_WORK = 3
    # MAX_TEXT_WORK = 10
    MAX_IMAGE_WORK = 10
    MAX_TEXT_WORK = 100
    TH_UPDATE_RATIO = 0.9
    
    def __init__(self, image_eval_func, text_eval_func):
        super().__init__(daemon=True)
        self.image_eval_func = image_eval_func
        self.text_eval_func = text_eval_func
        self.image_ready_queue: CustomQueue[QueueItem] = CustomQueue()
        self.text_ready_queue: CustomQueue[QueueItem] = CustomQueue()
        self.image_working_queue: CustomQueue[QueueWorker] = CustomQueue()
        self.text_working_queue: CustomQueue[QueueWorker] = CustomQueue()
        
        self.reset_img_th()
        self.reset_text_th()
    
    def put_image(self, data) -> QueueItem:
        item = QueueItem(data)
        self.image_ready_queue.put(item)
        return item
    
    def put_text(self, data) -> QueueItem:
        item = QueueItem(data)
        self.text_ready_queue.put(item)
        return item

    def lower_img_th(self):
        self.image_eval_th = self.image_eval_th * self.TH_UPDATE_RATIO
    
    def lower_text_th(self):
        self.text_eval_th = self.text_eval_th * self.TH_UPDATE_RATIO
    
    def reset_img_th(self):
        self.image_eval_th = self.MAX_IMAGE_WORK
    
    def reset_text_th(self):
        self.text_eval_th = self.MAX_TEXT_WORK

    def work_image(self, max_count=None):
        if max_count is None:
            max_count = self.MAX_IMAGE_WORK
        items = []
        for _ in range(max_count):
            item = self.image_ready_queue.get()
            if item is None:
                break
            items.append(item)
        if not items:
            return
        self.image_working_queue.put(QueueWorker(self.image_eval_func, items))

    def work_text(self, max_count=None):
        if max_count is None:
            max_count = self.MAX_TEXT_WORK
        items = []
        for _ in range(max_count):
            item = self.text_ready_queue.get()
            if item is None:
                break
            items.append(item)
        if not items:
            return
        self.text_working_queue.put(QueueWorker(self.text_eval_func, items))
    
    def run(self):
        while True:
            sleep(0.2)
            if (task := self.image_working_queue.peek()):
                if task.is_alive():
                    self.work_text()
                    self.reset_text_th()
                    continue
            if (task := self.text_working_queue.peek()):
                if task.is_alive():
                    continue
            image_count = self.image_ready_queue.count()
            text_count = self.text_ready_queue.count()
            if text_count > self.text_eval_th:
                self.work_text()
                self.reset_text_th()
                self.lower_img_th()
            elif image_count > self.image_eval_th:
                self.work_image()
                self.reset_img_th()
                self.lower_text_th()
            else:
                self.lower_img_th()
                self.lower_text_th()
            while (task := self.image_working_queue.peek()):
                if not task.is_alive():
                    self.image_working_queue.get()
                else:
                    break
            while (task := self.text_working_queue.peek()):
                if not task.is_alive():
                    self.text_working_queue.get()
                else:
                    break
