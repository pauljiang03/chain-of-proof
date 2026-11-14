import ChainOfProof.Check
import ChainOfProof.Sets

/-
  Facts about the checker itself, proved once for all inputs.
  These are what a proof assistant adds over running a checker script.
-/
namespace ChainOfProof

/-! ### What the bricks mean -/

theorem precedes_iff (x y : Fact) : precedes x y = true ↔ x.t + x.res + y.res < y.t := by
  simp [precedes]

theorem with1_iff (fs : List Fact) (a : Nat) (k : Fact → Bool) :
    with1 fs a k = true ↔ ∃ x, lookup fs a = some x ∧ k x = true := by
  unfold with1
  cases lookup fs a <;> simp

theorem with2_iff (fs : List Fact) (a b : Nat) (k : Fact → Fact → Bool) :
    with2 fs a b k = true ↔
      ∃ x y, lookup fs a = some x ∧ lookup fs b = some y ∧ k x y = true := by
  simp only [with2, with1_iff]
  constructor
  · rintro ⟨x, ha, y, hb, hk⟩; exact ⟨x, y, ha, hb, hk⟩
  · rintro ⟨x, y, ha, hb, hk⟩; exact ⟨x, ha, y, hb, hk⟩

/-- A certified `before a b` means: both facts are cited, and the gap between their
    timestamps exceeds the sum of their uncertainties. -/
theorem holds_before_iff (fs : List Fact) (a b : Nat) :
    holds fs (.before a b) = true ↔
      ∃ x y, lookup fs a = some x ∧ lookup fs b = some y ∧ x.t + x.res + y.res < y.t := by
  simp [holds, with2_iff, precedes_iff]

/-- A certified `link` means: both facts are cited and the two studs hold the same entity. -/
theorem holds_link_iff (fs : List Fact) (a b : Nat) (sa sb : Slot) :
    holds fs (.link a sa b sb) = true ↔
      ∃ x y, lookup fs a = some x ∧ lookup fs b = some y ∧ x.get sa = y.get sb := by
  simp [holds, with2_iff]

theorem holds_both_iff (fs : List Fact) (c d : Claim) :
    holds fs (.both c d) = true ↔ holds fs c = true ∧ holds fs d = true := by
  simp [holds]

/-- A kind assertion gives the exact cited row and its kind, not another kind's meaning. -/
theorem holds_is_iff (fs : List Fact) (a : Nat) (k : Kind) :
    holds fs (.is a k) = true ↔ ∃ x, lookup fs a = some x ∧ x.kind = k := by
  simp [holds, with1_iff]

theorem holds_is_kind_unique {fs : List Fact} {a : Nat} {k l : Kind}
    (hk : holds fs (.is a k) = true) (hl : holds fs (.is a l) = true) : k = l := by
  obtain ⟨x, hx, hkind⟩ := (holds_is_iff fs a k).mp hk
  obtain ⟨y, hy, hother⟩ := (holds_is_iff fs a l).mp hl
  have same : x = y := Option.some.inj (hx.symm.trans hy)
  subst y
  exact hkind.symm.trans hother

/-- The snapping lemma: two proven bricks give a proven bigger brick. -/
theorem holds_both {fs : List Fact} {c d : Claim}
    (h₁ : holds fs c = true) (h₂ : holds fs d = true) : holds fs (.both c d) = true := by
  show (holds fs c && holds fs d) = true
  rw [h₁, h₂]
  rfl

/-! ### Certified order is a strict partial order -/

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

/-- Two certified `before` bricks compose into a third: timelines can be chained. -/
theorem before_trans (fs : List Fact) (a b c : Nat)
    (h₁ : holds fs (.before a b) = true) (h₂ : holds fs (.before b c) = true) :
    holds fs (.before a c) = true := by
  simp only [holds, with2_iff] at *
  obtain ⟨x, y, ha, hb, hxy⟩ := h₁
  obtain ⟨y', z, hb', hc, hyz⟩ := h₂
  have : y = y' := Option.some.inj (hb.symm.trans hb')
  subst this
  exact ⟨x, z, ha, hc, precedes_trans hxy hyz⟩

/-- A certified timeline cannot place two events in both orders. -/
theorem before_asymm (fs : List Fact) (a b : Nat)
    (h : holds fs (.before a b) = true) : holds fs (.before b a) = false := by
  cases h' : holds fs (.before b a) with
  | false => rfl
  | true =>
    simp only [holds, with2_iff] at h h'
    obtain ⟨x, y, ha, hb, hxy⟩ := h
    obtain ⟨y', x', hb', ha', hyx⟩ := h'
    have : y = y' := Option.some.inj (hb.symm.trans hb')
    subst this
    have : x = x' := Option.some.inj (ha.symm.trans ha')
    subst this
    simp [precedes_asymm hxy] at hyx

/-! ### Certificates are stable under new evidence -/

theorem with1_mono {fs gs : List Fact}
    (h : ∀ i x, lookup fs i = some x → lookup gs i = some x) (a : Nat) (k : Fact → Bool)
    (hk : with1 fs a k = true) : with1 gs a k = true := by
  rw [with1_iff] at *
  obtain ⟨x, ha, hx⟩ := hk
  exact ⟨x, h a x ha, hx⟩

theorem with2_mono {fs gs : List Fact}
    (h : ∀ i x, lookup fs i = some x → lookup gs i = some x) (a b : Nat)
    (k : Fact → Fact → Bool) (hk : with2 fs a b k = true) : with2 gs a b k = true := by
  rw [with2_iff] at *
  obtain ⟨x, y, ha, hb, hxy⟩ := hk
  exact ⟨x, y, h a x ha, h b y hb, hxy⟩

/-- A brick proven on one fact list stays proven on any list that resolves the same
    ids to the same facts. So bricks proven on their own small lists can be reused
    inside a narrative's larger list. (Claims are positive; none says "no such fact".) -/
theorem holds_mono {fs gs : List Fact}
    (h : ∀ i x, lookup fs i = some x → lookup gs i = some x) (c : Claim)
    (hc : holds fs c = true) : holds gs c = true := by
  induction c with
  | both c d ihc ihd =>
    rw [holds_both_iff] at *
    exact ⟨ihc hc.1, ihd hc.2⟩
  | is f k => exact with1_mono h _ _ hc
  | val f s v => exact with1_mono h _ _ hc
  | link a sa b sb => exact with2_mono h _ _ _ hc
  | before a b => exact with2_mono h _ _ _ hc

theorem lookup_append {fs : List Fact} {i : Nat} {x : Fact} (extra : List Fact)
    (h : lookup fs i = some x) : lookup (fs ++ extra) i = some x := by
  simp [lookup, List.find?_append] at *
  simp [h]

/-- Evidence growth never invalidates a certificate. -/
theorem holds_append (fs extra : List Fact) (c : Claim)
    (h : holds fs c = true) : holds (fs ++ extra) c = true :=
  holds_mono (fun _ _ hx => lookup_append extra hx) c h

/-! ### What a set gives you -/

/-- A certified `usbMountedAs u m` really does cite a USB insert and a volume mapping
    that name the same device. -/
theorem usbMountedAs_sound (fs : List Fact) (u m : Nat)
    (h : holds fs (Sets.usbMountedAs u m) = true) :
    ∃ x y, lookup fs u = some x ∧ lookup fs m = some y ∧
      x.kind = .usbInsert ∧ y.kind = .volumeMount ∧ x.obj = y.obj := by
  unfold Sets.usbMountedAs at h
  rw [holds_both_iff, holds_both_iff] at h
  obtain ⟨h₁, h₂, h₃⟩ := h
  simp only [holds, with1_iff] at h₁ h₂
  simp only [holds, with2_iff] at h₃
  obtain ⟨x, hx, hkx⟩ := h₁
  obtain ⟨y, hy, hky⟩ := h₂
  obtain ⟨x', y', hx', hy', hl⟩ := h₃
  have : x = x' := Option.some.inj (hx.symm.trans hx')
  subst this
  have : y = y' := Option.some.inj (hy.symm.trans hy')
  subst this
  exact ⟨x, y, hx, hy, by simpa using hkx, by simpa using hky, by simpa [Fact.get] using hl⟩

/-- Journal removal has its own kind; it does not imply use of the Recycle Bin. -/
theorem fileRemoved_not_recycleBin (fs : List Fact) (a : Nat)
    (h : holds fs (Sets.fileRemovedAt a) = true) :
    holds fs (Sets.fileDeletedAt a) = false := by
  cases h' : holds fs (Sets.fileDeletedAt a) with
  | false => rfl
  | true => cases holds_is_kind_unique h h'

/-- An accumulated journal creation flag is not a filesystem creation timestamp. -/
theorem journalCreation_not_filesystemCreation (fs : List Fact) (a : Nat)
    (h : holds fs (Sets.fileCreationRecordedAt a) = true) :
    holds fs (Sets.fileCreatedAt a) = false := by
  cases h' : holds fs (Sets.fileCreatedAt a) with
  | false => rfl
  | true => cases holds_is_kind_unique h h'

/-- What the optical timeline set establishes: typed records, a common volume,
    and a timestamp gap greater than the two uncertainties. -/
theorem createdAfterVolumeRecord_sound (fs : List Fact) (c v : Nat)
    (h : holds fs (Sets.createdAfterVolumeRecord c v) = true) :
    ∃ x y, lookup fs c = some x ∧ lookup fs v = some y ∧
      x.kind = .fileCreated ∧ y.kind = .volumeRecorded ∧ x.aux = y.aux ∧
      y.t + y.res + x.res < x.t := by
  simp only [Sets.createdAfterVolumeRecord, holds_both_iff, holds_is_iff,
             holds_link_iff, holds_before_iff] at h
  obtain ⟨⟨x, hx, hkx⟩, ⟨y, hy, hky⟩, ⟨x', y', hx', hy', heq⟩,
           ⟨y'', x'', hy'', hx'', ht⟩⟩ := h
  have : x = x' := Option.some.inj (hx.symm.trans hx')
  subst x'
  have : y = y' := Option.some.inj (hy.symm.trans hy')
  subst y'
  have : x = x'' := Option.some.inj (hx.symm.trans hx'')
  subst x''
  have : y = y'' := Option.some.inj (hy.symm.trans hy'')
  subst y''
  exact ⟨x, y, hx, hy, hkx, hky, by simpa [Fact.get] using heq, ht⟩

/-- Name equality here is equality of scoped NTFS identities, never path similarity. -/
theorem sameJournalFile_sound (fs : List Fact) (a b : Nat)
    (h : holds fs (Sets.sameJournalFile a b) = true) :
    ∃ x y, lookup fs a = some x ∧ lookup fs b = some y ∧
      x.kind = .journalName ∧ y.kind = .journalName ∧ x.aux = y.aux := by
  simp only [Sets.sameJournalFile, holds_both_iff, holds_is_iff, holds_link_iff] at h
  obtain ⟨⟨x, hx, hkx⟩, ⟨y, hy, hky⟩, ⟨x', y', hx', hy', heq⟩⟩ := h
  have : x = x' := Option.some.inj (hx.symm.trans hx')
  subst x'
  have : y = y' := Option.some.inj (hy.symm.trans hy')
  subst y'
  exact ⟨x, y, hx, hy, hkx, hky, by simpa [Fact.get] using heq⟩

/-- Linking an old name to a removal flag preserves identity and strict observation order. -/
theorem removedFilePreviouslyNamed_sound (fs : List Fact) (n r : Nat)
    (h : holds fs (Sets.removedFilePreviouslyNamed n r) = true) :
    ∃ x y, lookup fs n = some x ∧ lookup fs r = some y ∧
      x.kind = .journalName ∧ y.kind = .journalRemoval ∧ x.aux = y.aux ∧
      x.t + x.res + y.res < y.t := by
  simp only [Sets.removedFilePreviouslyNamed, holds_both_iff, holds_is_iff,
             holds_link_iff, holds_before_iff] at h
  obtain ⟨⟨x, hx, hkx⟩, ⟨y, hy, hky⟩, ⟨x', y', hx', hy', heq⟩,
           ⟨x'', y'', hx'', hy'', ht⟩⟩ := h
  have : x = x' := Option.some.inj (hx.symm.trans hx')
  subst x'
  have : y = y' := Option.some.inj (hy.symm.trans hy')
  subst y'
  have : x = x'' := Option.some.inj (hx.symm.trans hx'')
  subst x''
  have : y = y'' := Option.some.inj (hy.symm.trans hy'')
  subst y''
  exact ⟨x, y, hx, hy, hkx, hky, by simpa [Fact.get] using heq, ht⟩

/-- The two identity joins needed to name a child's separately observed directory. -/
theorem journalChildNamedDirectory_sound (fs : List Fact) (c p d : Nat)
    (h : holds fs (Sets.journalChildNamedDirectory c p d) = true) :
    ∃ x y z, lookup fs c = some x ∧ lookup fs p = some y ∧ lookup fs d = some z ∧
      x.kind = .journalName ∧ y.kind = .journalParent ∧ z.kind = .journalName ∧
      x.aux = y.obj ∧ y.aux = z.aux := by
  simp only [Sets.journalChildNamedDirectory, holds_both_iff, holds_is_iff, holds_link_iff] at h
  obtain ⟨⟨x, hx, hkx⟩, ⟨y, hy, hky⟩, ⟨z, hz, hkz⟩,
           ⟨x', y', hx', hy', hxy⟩, ⟨y'', z', hy'', hz', hyz⟩⟩ := h
  have : x = x' := Option.some.inj (hx.symm.trans hx')
  subst x'
  have : y = y' := Option.some.inj (hy.symm.trans hy')
  subst y'
  have : y = y'' := Option.some.inj (hy.symm.trans hy'')
  subst y''
  have : z = z' := Option.some.inj (hz.symm.trans hz')
  subst z'
  exact ⟨x, y, z, hx, hy, hz, hkx, hky, hkz,
         by simpa [Fact.get] using hxy, by simpa [Fact.get] using hyz⟩

/-- A typed journal name cannot be promoted to a filesystem creation event. -/
theorem journalName_not_filesystemCreation (fs : List Fact) (a : Nat)
    (h : holds fs (Sets.journalNamed a) = true) :
    holds fs (Sets.fileCreatedAt a) = false := by
  cases h' : holds fs (Sets.fileCreatedAt a) with
  | false => rfl
  | true => cases holds_is_kind_unique h h'

end ChainOfProof
