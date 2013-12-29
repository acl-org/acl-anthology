class Venue < ActiveRecord::Base
	has_many :events
  	validates_associated :events
  	accepts_nested_attributes_for :events
end
