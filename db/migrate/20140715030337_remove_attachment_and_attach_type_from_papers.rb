class RemoveAttachmentAndAttachTypeFromPapers < ActiveRecord::Migration
  def change
    remove_column :papers, :attachment, :string
    remove_column :papers, :attach_type, :string
  end
end
