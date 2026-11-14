import ChainOfProof
open ChainOfProof

namespace Cert.A050

def cited : List Fact := [
  ⟨8864, .fileRenamed, 1427142644624013, 1, 12526, 12527⟩,
  ⟨8865, .fileRenamed, 1427142662909250, 1, 12528, 12529⟩,
  ⟨2285, .cloudFile, 1427142755056000, 1000, 1422, 1426⟩,
  ⟨2286, .cloudFile, 1427142755072000, 1000, 1424, 1426⟩,
  ⟨2290, .cloudFile, 1427142757552000, 1000, 1422, 1429⟩,
  ⟨2289, .cloudFile, 1427142757552000, 1000, 1424, 1429⟩,
  ⟨2300, .cloudFile, 1427142875655000, 1000, 1422, 1430⟩,
  ⟨2296, .cloudFile, 1427142865884000, 1000, 1424, 1430⟩,
  ⟨2302, .cloudFile, 1427143336964000, 1000, 1422, 1428⟩,
  ⟨2301, .cloudFile, 1427143336964000, 1000, 1424, 1428⟩ ]

def claim : Claim := .both (Sets.renamed 8864) (.both (Sets.renamed 8865) (.both (Sets.cloudEvent 2285) (.both (Sets.cloudEvent 2286) (.both (Sets.cloudEvent 2290) (.both (Sets.cloudEvent 2289) (.both (Sets.cloudEvent 2300) (.both (Sets.cloudEvent 2296) (.both (Sets.cloudEvent 2302) (Sets.cloudEvent 2301)))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A050

#print axioms Cert.A050.verified
