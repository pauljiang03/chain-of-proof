import ChainOfProof
open ChainOfProof

namespace Cert.A052

def cited : List Fact := [
  ⟨2290, .cloudFile, 1427142757552000, 1000, 1422, 1429⟩,
  ⟨2302, .cloudFile, 1427143336964000, 1000, 1422, 1428⟩ ]

def claim : Claim := .before 2290 2302

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A052

#print axioms Cert.A052.verified
