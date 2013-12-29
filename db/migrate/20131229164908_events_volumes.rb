class EventsVolumes < ActiveRecord::Migration
  def change
  	create_table :events_volumes, :id => false do |t|
    	t.integer :event_id
    	t.integer :volume_id
  	end
  end
end
