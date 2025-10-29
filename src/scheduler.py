from collections import deque
from threading import Thread, Event, Lock
from time import sleep

class CustomQueue:
    def __init__(self):
        self.queue = deque()
        self.lock = Lock()
    
    def put(self, item):
        with self.lock:
            self.queue.append(item)
    
    def get(self):
        with self.lock:
            return self.queue.popleft() if self.queue else None

    def peek(self):
        with self.lock:
            return self.queue[0] if self.queue else None

    def count(self):
        with self.lock:
            return len(self.queue)


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


class QueueWorker(Thread):
    def __init__(self, func, items: list[QueueItem]):
        super().__init__()
        self.func = func
        self.items = items
        self.start()
    
    def run(self):
        datas = [item.data for item in self.items]
        results = self.func(datas)
        for item, result in zip(self.items, results):
            item.set_result(result)


class TaskQueue(Thread):
    MAX_IMAGE_WORK = 3
    MAX_TEXT_WORK = 10
    
    def __init__(self, image_eval_func, text_eval_func):
        self.image_eval_func = image_eval_func
        self.text_eval_func = text_eval_func
        self.image_ready_queue = CustomQueue()
        self.text_ready_queue = CustomQueue()
        self.image_working_queue = CustomQueue()
        self.text_working_queue = CustomQueue()
    
    def put_image(self, data):
        item = QueueItem(data)
        self.image_ready_queue.put(item)
        return item
    
    def put_text(self, data):
        item = QueueItem(data)
        self.text_ready_queue.put(data)
        return item

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
            image_weight = self.image_ready_queue.count() * 5
            text_weight = self.text_ready_queue.count()
            if image_weight > text_weight + 5:
                self.work_image()
            elif abs(image_weight - text_weight) <= 5:
                self.work_image(1)
                self.work_text(5)
            else:
                self.work_text()
            sleep(0.2)
