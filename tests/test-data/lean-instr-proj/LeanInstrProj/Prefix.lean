



inductive Exp where
  | num (a : Nat)
  | add (e1 e2 : Exp)
  | var (s : String)


def cfold : Exp → Exp
  | Exp.num n => Exp.num n
  | Exp.add (Exp.num n1) (Exp.num n2) => Exp.num (n1 + n2)
  | Exp.add e1 e2 => Exp.add (cfold e1) (cfold e2)
  | Exp.var s => Exp.var s

#eval 1 + "foo".length

def eval (Γ : String → Nat) : Exp → Nat
  | Exp.num a => a
  | Exp.add a1 a2 => eval Γ a1 + eval Γ a2
  | Exp.var s => Γ s


theorem prefix1 (Γ : String → Nat) (e : Exp) :
  eval Γ (cfold e) = eval Γ e := by
  induction e using cfold.induct with
  | case1 => simp [cfold]


theorem prefix2 (Γ : String → Nat) (e : Exp) :
  eval Γ (cfold e) = eval Γ e := by
  induction e using cfold.induct with
  | case1 => simp [cfold]
  | case2 => simp [cfold]
  | case3 => sorry
  | case4 => simp [cfold]


theorem prefix3 (Γ : String → Nat) (e : Exp) :
  eval Γ (cfold e) = eval Γ e := by
  induction e using cfold.induct e with
  | case1 => simp [cfold]
  | case2 => simp [cfold]
  | case3 => sorry
  | case4 => simp [cfold]


theorem prefix4 (Γ : String → Nat) (e : Exp) :
  eval Γ (cfold e) = eval Γ e := by
  si
