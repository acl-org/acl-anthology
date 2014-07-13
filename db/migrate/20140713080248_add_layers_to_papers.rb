class AddLayersToPapers < ActiveRecord::Migration
  def change
    add_column :papers, :layers, :string
  end
end
