class CreateEvents < ActiveRecord::Migration
  def change
    create_table :events do |t|
      t.integer :year
      t.integer :venue_id
      t.string :kind

      t.timestamps
    end

    add_column :events, :slug, :string
    add_index :events, :slug, unique: true
  end
end
