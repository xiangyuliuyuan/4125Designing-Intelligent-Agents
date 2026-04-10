class Counter:
    """垃圾收集计数器"""

    def __init__(self):
        self.dirtCollected = 0
        self.collected_label = None
        self.debris_label = None
        self.initial_debris = 0

    def set_collected_label(self, label):
        self.collected_label = label
        self.update_collected_display()

    def set_debris_label(self, label):
        self.debris_label = label

    def set_initial_debris(self, count):
        self.initial_debris = count
        self.update_debris_display(0)

    def update_collected_display(self):
        if self.collected_label:
            self.collected_label.set(str(self.dirtCollected))

    def update_debris_display(self, current_debris):
        if self.debris_label:
            self.debris_label.set(str(current_debris))

    def itemCollected(self, *_args):
        """Increment the collected-dirt counter.

        Accepts (and ignores) any positional arguments for backward
        compatibility with call sites that still pass ``canvas`` and
        ``debris_count``.
        """
        self.dirtCollected += 1
        self.update_collected_display()