import ChainOfProof
open ChainOfProof

namespace Cert.M279

def cited : List Fact := [
  ⟨2272, .cloudFile, 1422563714000000, 1000000, 1422, 1423⟩,
  ⟨2273, .cloudFile, 1422563714530000, 10000, 1422, 1423⟩,
  ⟨2274, .cloudFile, 1422636560000000, 1000000, 1424, 1423⟩,
  ⟨2275, .cloudFile, 1422636560550000, 10000, 1424, 1423⟩,
  ⟨2276, .cloudFile, 1424722168000000, 1000000, 1425, 1426⟩,
  ⟨2277, .cloudFile, 1424722168000000, 1000000, 1425, 1423⟩,
  ⟨2278, .cloudFile, 1424722168000000, 1000000, 1425, 1423⟩,
  ⟨2279, .cloudFile, 1427141134013000, 1000, 1425, 1427⟩,
  ⟨2280, .cloudFile, 1427141137746000, 1000, 1425, 1427⟩,
  ⟨2281, .cloudFile, 1427141165240000, 10000, 1425, 1428⟩,
  ⟨2282, .cloudFile, 1427141167426000, 1000, 1425, 1428⟩,
  ⟨2283, .cloudFile, 1427141168000000, 1000000, 1425, 1428⟩,
  ⟨2284, .cloudFile, 1427141168456000, 1000, 1425, 1428⟩,
  ⟨2285, .cloudFile, 1427142755056000, 1000, 1422, 1426⟩,
  ⟨2286, .cloudFile, 1427142755072000, 1000, 1424, 1426⟩,
  ⟨2287, .cloudFile, 1427142755072000, 1000, 1424, 1423⟩,
  ⟨2288, .cloudFile, 1427142755072000, 1000, 1422, 1423⟩,
  ⟨2289, .cloudFile, 1427142757552000, 1000, 1424, 1429⟩,
  ⟨2290, .cloudFile, 1427142757552000, 1000, 1422, 1429⟩,
  ⟨2291, .cloudFile, 1427142762000000, 1000000, 1422, 1426⟩,
  ⟨2292, .cloudFile, 1427142765000000, 1000000, 1424, 1426⟩,
  ⟨2293, .cloudFile, 1427142765415000, 1000, 1424, 1429⟩,
  ⟨2294, .cloudFile, 1427142765415000, 1000, 1422, 1429⟩,
  ⟨2295, .cloudFile, 1427142854000000, 1000000, 1424, 1423⟩,
  ⟨2296, .cloudFile, 1427142865884000, 1000, 1424, 1430⟩,
  ⟨2297, .cloudFile, 1427142865884000, 1000, 1424, 1430⟩,
  ⟨2298, .cloudFile, 1427142870000000, 1000000, 1422, 1423⟩,
  ⟨2299, .cloudFile, 1427142875655000, 1000, 1422, 1430⟩,
  ⟨2300, .cloudFile, 1427142875655000, 1000, 1422, 1430⟩,
  ⟨2301, .cloudFile, 1427143336964000, 1000, 1424, 1428⟩,
  ⟨2302, .cloudFile, 1427143336964000, 1000, 1422, 1428⟩,
  ⟨2303, .cloudFile, 1427143339000000, 1000000, 1422, 1428⟩,
  ⟨2304, .cloudFile, 1427143339369000, 1000, 1424, 1428⟩,
  ⟨2305, .cloudFile, 1427143339385000, 1000, 1422, 1428⟩,
  ⟨2306, .cloudFile, 1427143340072000, 1000, 1422, 1428⟩,
  ⟨2307, .cloudFile, 1427143342000000, 1000000, 1424, 1428⟩,
  ⟨2308, .cloudFile, 1427143342709000, 1000, 1424, 1428⟩ ]

def claim : Claim := .both (Sets.cloudEvent 2272) (.both (Sets.cloudEvent 2273) (.both (Sets.cloudEvent 2274) (.both (Sets.cloudEvent 2275) (.both (Sets.cloudEvent 2276) (.both (Sets.cloudEvent 2277) (.both (Sets.cloudEvent 2278) (.both (Sets.cloudEvent 2279) (.both (Sets.cloudEvent 2280) (.both (Sets.cloudEvent 2281) (.both (Sets.cloudEvent 2282) (.both (Sets.cloudEvent 2283) (.both (Sets.cloudEvent 2284) (.both (Sets.cloudEvent 2285) (.both (Sets.cloudEvent 2286) (.both (Sets.cloudEvent 2287) (.both (Sets.cloudEvent 2288) (.both (Sets.cloudEvent 2289) (.both (Sets.cloudEvent 2290) (.both (Sets.cloudEvent 2291) (.both (Sets.cloudEvent 2292) (.both (Sets.cloudEvent 2293) (.both (Sets.cloudEvent 2294) (.both (Sets.cloudEvent 2295) (.both (Sets.cloudEvent 2296) (.both (Sets.cloudEvent 2297) (.both (Sets.cloudEvent 2298) (.both (Sets.cloudEvent 2299) (.both (Sets.cloudEvent 2300) (.both (Sets.cloudEvent 2301) (.both (Sets.cloudEvent 2302) (.both (Sets.cloudEvent 2303) (.both (Sets.cloudEvent 2304) (.both (Sets.cloudEvent 2305) (.both (Sets.cloudEvent 2306) (.both (Sets.cloudEvent 2307) (Sets.cloudEvent 2308))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M279

#print axioms Cert.M279.verified
