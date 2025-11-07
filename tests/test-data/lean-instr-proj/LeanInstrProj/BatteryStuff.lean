import Batteries.Data.Rat

theorem rat_to_float : ∀ r, Rat.toFloat r = Rat.toFloat r := by
  intros; rfl
