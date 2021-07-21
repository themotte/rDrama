class PaymentRequired(Exception):
	status_code=402
	def __init__(self):
		Exception.__init__(self)
		self.status_code=402
