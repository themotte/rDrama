import requests
from os import environ
from sqlalchemy import *
from sqlalchemy.orm import relationship
from .mix_ins import *
from drama.__main__ import Base, app

PAYPAL_ID=environ.get("PAYPAL_CLIENT_ID", "").strip()
PAYPAL_SECRET=environ.get("PAYPAL_CLIENT_SECRET", "").strip()
PAYPAL_WEBHOOK_ID=environ.get("PAYPAL_WEBHOOK_ID", "").strip()

PAYPAL_URL="https://api.paypal.com"

STATUSES={
	1:"CREATED",
	2:"AUTHORIZED",
	3:"CAPTURED",
	-2:"REVERSED"
}

class PayPalClient():

	def __init__(self):

		self.paypal_token=None
		self.token_expires=0
		self.webhook_id=PAYPAL_WEBHOOK_ID

	def print(self, x):

		try:
			print(x)
		except OSError:
			pass

	def new_token(self):

		url=f"{PAYPAL_URL}/v1/oauth2/token"

		headers={
			"Accept":"application/json"
		}

		data={
			"grant_type":"client_credentials"
		}

		x=requests.post(url, headers=headers, data=data, auth=(PAYPAL_ID,PAYPAL_SECRET))

		x=x.json()

		self.paypal_token=x["access_token"]
		self.token_expires=int(time.time())+int(x["expires_in"])

	def _get(self, url):

		if time.time()>self.token_expires:
			self.new_token()

		url=PAYPAL_URL+url

		headers={
			"Content-Type":"application/json",
		#	"Accept":"application/json",
			"Authorization":f"Bearer {self.paypal_token}"
			}

		return requests.get(url, headers=headers)


	def _post(self, url, data=None):

		if time.time()>self.token_expires:
			self.new_token()

		url=PAYPAL_URL+url

		headers={
			"Content-Type":"application/json",
		#	"Accept":"application/json",
			"Authorization":f"Bearer {self.paypal_token}"
			}

		return requests.post(url, headers=headers, json=data)

	def create(self, txn):

		if not txn.id:
			raise ValueError("txn must be flushed first")

		url="/v2/checkout/orders"

		data={
			"intent":"CAPTURE",
			"purchase_units":
			[
				{
				"amount": {
					"currency_code":"USD",
					"value": str(txn.usd_cents/100)
					}
				}
			],
			"application_context":{
				"return_url":f"https://{app.config['SERVER_NAME']}/shop/buy_coins_completed?txid={txn.base36id}"
			}
		}

		r=self._post(url, data=data)

		x=r.json()

		if x["status"]=="CREATED":
			txn.paypal_id=x["id"]
			txn.status=1

	def authorize(self, txn):

		url=f"{txn.paypal_url}/authorize"

		x= self._post(url)
		x=x.json()

		status=x["status"]
		if status in ["SAVED", "COMPLETED"]:
			txn.status=2

		return x["status"] in ["SAVED", "COMPLETED"]


	def capture(self, txn):

		url=f"{txn.paypal_url}/capture"

		x=self._post(url)
		x=x.json()
		
		try:
			status=x["status"]
			if status=="COMPLETED":
				txn.status=3
		except KeyError:
			abort(403)
			
		return status=="COMPLETED"


class PayPalTxn(Base, Stndrd, Age_times):

	__tablename__="paypal_txns"

	id=Column(Integer, primary_key=True)
	user_id=Column(Integer, ForeignKey("users.id"))
	created_utc=Column(Integer)
	paypal_id=Column(String)
	usd_cents=Column(Integer)
	coin_count=Column(Integer)
	promo_id=Column(Integer, ForeignKey("promocodes.id"))

	status=Column(Integer, default=0) #0=initialized 1=created, 2=authorized, 3=captured, -1=failed, -2=reversed 

	user=relationship("User", lazy="joined")
	promo=relationship("PromoCode", lazy="joined")

	@property
	def approve_url(self):

		return f"https://www.paypal.com/checkoutnow?token={self.paypal_id}"

	@property
	def paypal_url(self):

		return f"/v2/checkout/orders/{self.paypal_id}"

	@property
	def permalink(self):
		return f"/paypaltxn/{self.base36id}"

	@property
	def display_usd(self):
		s=str(self.usd_cents)
		d=s[0:-2] or '0'
		c=s[-2:]
		return f"${d}.{c}"

	@property
	def status_text(self):
		return STATUSES[self.status]

class PromoCode(Base):

	__tablename__="promocodes"

	id=Column(Integer, primary_key=True)
	code=Column(String(64))
	is_active=Column(Boolean)
	percent_off=Column(Integer, default=None)
	flat_cents_off=Column(Integer, default=None)
	flat_cents_min=Column(Integer, default=None)
	promo_start_utc=Column(Integer, default=None)
	promo_end_utc=Column(Integer, default=None)
	promo_info=Column(String(64), default=None)

	def adjust_price(self, cents):

		now=int(time.time())

		if self.promo_start_utc and now < self.promo_start_utc:
			return cents

		elif self.promo_end_utc and now > self.promo_end_utc:
			return cents

		if not self.is_active:
			return cents

		if self.percent_off:
			x = (100-self.percent_off)/100
			return int(cents * x)

		if self.flat_cents_off:
			if cents >= self.flat_cents_min:
				cents -= self.flat_cents_off
			return cents

		else:
			return cents

	@property
	def display_flat_off(self):
		s=str(self.flat_cents_off)
		d=s[0:-2] or '0'
		c=s[-2:]
		return f"${d}.{c}"

	@property
	def display_flat_min(self):
		s=str(self.flat_cents_min)
		d=s[0:-2] or '0'
		c=s[-2:]
		return f"${d}.{c}"

	@property
	def promo_text(self):

		now=int(time.time())

		if self.promo_start_utc and now < self.promo_start_utc:
			return f"This promotion hasn't started yet. Try again later."

		elif self.promo_end_utc and now > self.promo_end_utc:
			return f"This promotion has already ended. Sorry about that."

		elif self.percent_off:
			text= f"Save {self.percent_off}% on all purchases with code {self.code}."

		elif self.flat_cents_off and self.flat_cents_min:
			text= f"Save {self.display_flat_off} on any purchase over {self.display_flat_min} with code {self.code}."

		if self.promo_info:
			text += f" Your purchase will also support {self.promo_info}."

		return text
	


class AwardRelationship(Base):

	__tablename__="award_relationships"

	id=Column(Integer, primary_key=True)

	user_id=Column(Integer, ForeignKey("users.id"))
	submission_id=Column(Integer, ForeignKey("submissions.id"), default=None)
	comment_id=Column(Integer, ForeignKey("comments.id"), default=None)