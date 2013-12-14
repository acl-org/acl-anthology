# Be sure to restart your server when you modify this file.

# Your secret key is used for verifying the integrity of signed cookies.
# If you change this key, all old signed cookies will become invalid!

# Make sure the secret is at least 30 characters and all random,
# no regular words or you'll be exposed to dictionary attacks.
# You can use `rake secret` to generate a secure secret key.

# Make sure your secret_key_base is kept private
# if you're sharing your code publicly.
Acl2::Application.config.secret_token = '462a2f23950e306261908d6e5519ffe41ce626b119e9fc03a012ba86f66d82ef32d42f283633bacc2f59cf96ce5968552fe94d154e4f00560c1214d6592dda09'
Acl2::Application.config.secret_key_base = '8e9a6f961325cd919e6b3a66e4691cf44186e19da4ef90281468b8b8d95eab63a962fa53e9d00f3ae8bc69c3cbfc806b099b9e305e34dc661b9a5dd191a44ef2'
