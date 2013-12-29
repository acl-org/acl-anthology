class CreateEvents < ActiveRecord::Migration
  def change
    create_table :events do |t|
      t.integer :year
      t.integer :venue_id
      t.string :type

      t.timestamps
    end
  end
end
