import ChainOfProof.Check

/-
  Facts about the checker itself, proved once for all inputs.
  These are what a proof assistant adds over running a checker script.
-/
namespace ChainOfProof

theorem precedes_iff (x y : Fact) : precedes x y = true ↔ x.t + x.res + y.res < y.t := by
  simp [precedes]

/-- No event precedes itself. -/
theorem precedes_irrefl (x : Fact) : precedes x x = false := by
  cases h : precedes x x with
  | false => rfl
  | true => rw [precedes_iff] at h; omega

/-- Certified order never runs both ways. -/
theorem precedes_asymm {x y : Fact} (h : precedes x y = true) : precedes y x = false := by
  cases h' : precedes y x with
  | false => rfl
  | true => rw [precedes_iff] at h h'; omega

/-- Certified order chains, even across sources with different timestamp resolution. -/
theorem precedes_trans {x y z : Fact}
    (h₁ : precedes x y = true) (h₂ : precedes y z = true) : precedes x z = true := by
  rw [precedes_iff] at *; omega

/-- A conjunction is certified exactly when both parts are. -/
theorem holds_both (fs : List Fact) (c d : Claim) :
    holds fs (.both c d) = true ↔ holds fs c = true ∧ holds fs d = true := by
  simp [holds]

/-- Two certified `before` findings compose into a third: timelines can be chained. -/
theorem before_trans (fs : List Fact) (a b c : Nat)
    (h₁ : holds fs (.before a b) = true) (h₂ : holds fs (.before b c) = true) :
    holds fs (.before a c) = true := by
  simp only [holds] at *
  cases ha : lookup fs a <;> cases hb : lookup fs b <;> cases hc : lookup fs c <;>
    simp_all
  exact precedes_trans h₁ h₂

/-- A certified timeline has no cycles of length two. -/
theorem before_asymm (fs : List Fact) (a b : Nat)
    (h : holds fs (.before a b) = true) : holds fs (.before b a) = false := by
  simp only [holds] at *
  cases ha : lookup fs a <;> cases hb : lookup fs b <;> simp_all
  exact precedes_asymm h

theorem lookup_append {fs : List Fact} {i : Nat} {x : Fact} (extra : List Fact)
    (h : lookup fs i = some x) : lookup (fs ++ extra) i = some x := by
  simp [lookup, List.find?_append] at *
  simp [h]

/-- Evidence growth never invalidates a certificate: adding facts keeps every
    certified claim certified. (Claims are positive; nothing here says "no such fact".) -/
theorem holds_append (fs extra : List Fact) (c : Claim)
    (h : holds fs c = true) : holds (fs ++ extra) c = true := by
  induction c with
  | both c d ihc ihd =>
    rw [holds_both] at *
    exact ⟨ihc h.1, ihd h.2⟩
  | before a b =>
    simp only [holds] at *
    cases ha : lookup fs a <;> cases hb : lookup fs b <;> simp_all
    simp [lookup_append extra ha, lookup_append extra hb, h]
  | sameDevice a b =>
    simp only [holds] at *
    cases ha : lookup fs a <;> cases hb : lookup fs b <;> simp_all
    simp [lookup_append extra ha, lookup_append extra hb, h]
  | onVolume a b =>
    simp only [holds] at *
    cases ha : lookup fs a <;> cases hb : lookup fs b <;> simp_all
    simp [lookup_append extra ha, lookup_append extra hb, h]
  | copied a b =>
    simp only [holds] at *
    cases ha : lookup fs a <;> cases hb : lookup fs b <;> simp_all
    simp [lookup_append extra ha, lookup_append extra hb, h]

end ChainOfProof
