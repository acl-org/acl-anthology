# -*- encoding : utf-8 -*-
class CreateBookmarks < ActiveRecord::Migration
  def self.up
    create_table :bookmarks do |t|
      t.integer :user_id, :null=>false
      t.text :url
      t.string :document_id
      t.string :title
      t.text :notes
      t.timestamps
    end
  end

  def self.down
    drop_table :bookmarks
  end
  
end
