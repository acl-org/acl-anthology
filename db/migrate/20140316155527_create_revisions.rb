class CreateRevisions < ActiveRecord::Migration
  def change
    create_table :revisions do |t|
      t.integer :paper_id
      t.integer :ver
      t.string :title

      t.timestamps
    end
  end
end
