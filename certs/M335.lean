import ChainOfProof
open ChainOfProof

namespace Cert.M335

def cited : List Fact := [
  ⟨12723, .fileContent, 1794614400000000, 1, 102, 16125⟩,
  ⟨12724, .fileContent, 1794614400000000, 1, 103, 16147⟩,
  ⟨12725, .fileContent, 1794614400000000, 1, 104, 16148⟩,
  ⟨12726, .fileContent, 1794614400000000, 1, 105, 16149⟩,
  ⟨12727, .fileContent, 1794614400000000, 1, 106, 16150⟩,
  ⟨12728, .fileContent, 1794614400000000, 1, 107, 16151⟩,
  ⟨12729, .fileContent, 1794614400000000, 1, 108, 16152⟩,
  ⟨12730, .fileContent, 1794614400000000, 1, 87, 16153⟩,
  ⟨12731, .fileContent, 1794614400000000, 1, 68, 16154⟩,
  ⟨12732, .fileContent, 1794614400000000, 1, 70, 16155⟩,
  ⟨12733, .fileContent, 1794614400000000, 1, 71, 16156⟩,
  ⟨12734, .fileContent, 1794614400000000, 1, 72, 16157⟩,
  ⟨12735, .fileContent, 1794614400000000, 1, 73, 16158⟩,
  ⟨12736, .fileContent, 1794614400000000, 1, 74, 16159⟩,
  ⟨12737, .fileContent, 1794614400000000, 1, 75, 16160⟩,
  ⟨12738, .fileContent, 1794614400000000, 1, 76, 16161⟩,
  ⟨12739, .fileContent, 1794614400000000, 1, 77, 16162⟩,
  ⟨12740, .fileContent, 1794614400000000, 1, 78, 16163⟩,
  ⟨12741, .fileContent, 1794614400000000, 1, 79, 16164⟩,
  ⟨12742, .fileContent, 1794614400000000, 1, 80, 16165⟩,
  ⟨12743, .fileContent, 1794614400000000, 1, 81, 16166⟩,
  ⟨12744, .fileContent, 1794614400000000, 1, 82, 16167⟩,
  ⟨12745, .fileContent, 1794614400000000, 1, 83, 16168⟩,
  ⟨12746, .fileContent, 1794614400000000, 1, 84, 16169⟩,
  ⟨12747, .fileContent, 1794614400000000, 1, 85, 16170⟩,
  ⟨12748, .fileContent, 1794614400000000, 1, 86, 16171⟩,
  ⟨12749, .fileContent, 1794614400000000, 1, 88, 16172⟩,
  ⟨12750, .fileContent, 1794614400000000, 1, 89, 16173⟩,
  ⟨12751, .fileContent, 1794614400000000, 1, 90, 16174⟩,
  ⟨12752, .fileContent, 1794614400000000, 1, 91, 16175⟩,
  ⟨12753, .fileContent, 1794614400000000, 1, 110, 16123⟩,
  ⟨12754, .fileContent, 1794614400000000, 1, 34, 16122⟩,
  ⟨12755, .fileContent, 1794614400000000, 1, 112, 16123⟩,
  ⟨12756, .fileContent, 1794614400000000, 1, 113, 16122⟩,
  ⟨12757, .fileContent, 1794614400000000, 1, 114, 16140⟩,
  ⟨12758, .fileContent, 1794614400000000, 1, 116, 16141⟩,
  ⟨12759, .fileContent, 1794614400000000, 1, 118, 16142⟩,
  ⟨12760, .fileContent, 1794614400000000, 1, 120, 16143⟩,
  ⟨12761, .fileContent, 1794614400000000, 1, 115, 16140⟩,
  ⟨12762, .fileContent, 1794614400000000, 1, 117, 16141⟩ ]

def claim : Claim := .both (Sets.contentHashed 12723) (.both (Sets.contentHashed 12724) (.both (Sets.contentHashed 12725) (.both (Sets.contentHashed 12726) (.both (Sets.contentHashed 12727) (.both (Sets.contentHashed 12728) (.both (Sets.contentHashed 12729) (.both (Sets.contentHashed 12730) (.both (Sets.contentHashed 12731) (.both (Sets.contentHashed 12732) (.both (Sets.contentHashed 12733) (.both (Sets.contentHashed 12734) (.both (Sets.contentHashed 12735) (.both (Sets.contentHashed 12736) (.both (Sets.contentHashed 12737) (.both (Sets.contentHashed 12738) (.both (Sets.contentHashed 12739) (.both (Sets.contentHashed 12740) (.both (Sets.contentHashed 12741) (.both (Sets.contentHashed 12742) (.both (Sets.contentHashed 12743) (.both (Sets.contentHashed 12744) (.both (Sets.contentHashed 12745) (.both (Sets.contentHashed 12746) (.both (Sets.contentHashed 12747) (.both (Sets.contentHashed 12748) (.both (Sets.contentHashed 12749) (.both (Sets.contentHashed 12750) (.both (Sets.contentHashed 12751) (.both (Sets.contentHashed 12752) (.both (Sets.contentHashed 12753) (.both (Sets.contentHashed 12754) (.both (Sets.contentHashed 12755) (.both (Sets.contentHashed 12756) (.both (Sets.contentHashed 12757) (.both (Sets.contentHashed 12758) (.both (Sets.contentHashed 12759) (.both (Sets.contentHashed 12760) (.both (Sets.contentHashed 12761) (Sets.contentHashed 12762)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M335

#print axioms Cert.M335.verified
