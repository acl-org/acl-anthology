class User < ActiveRecord::Base

  attr_accessible :email, :password, :password_confirmation if Rails::VERSION::MAJOR < 4
# Connects this user object to Blacklights Bookmarks. 
  include Blacklight::User
  # Include default devise modules. Others available are:
  # :confirmable, :lockable, :timeoutable and :omniauthable
  devise :database_authenticatable, :registerable,
         :recoverable, :rememberable, :trackable, :validatable

            # Method added by Blacklight; Blacklight uses #to_s on your
            # user class to get a user-displayable login/identifier for
            # the account.
            def to_s
              email
            end
          end
