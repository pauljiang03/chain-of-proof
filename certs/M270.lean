import ChainOfProof
open ChainOfProof

namespace Cert.M270

def cited : List Fact := [
  ⟨1995, .webVisit, 1427143468818928, 1, 1288, 1095⟩,
  ⟨1996, .webVisit, 1427143468821428, 1, 1288, 1095⟩,
  ⟨1997, .webVisit, 1427143470233959, 1, 1289, 1095⟩,
  ⟨1998, .webVisit, 1427143470253960, 1, 1289, 1095⟩,
  ⟨1999, .webVisit, 1427143471940487, 1, 1290, 1095⟩,
  ⟨2000, .webVisit, 1427143479967053, 1, 1291, 1095⟩,
  ⟨2001, .webVisit, 1427143488995155, 1, 1292, 1095⟩,
  ⟨2002, .webVisit, 1427143488997655, 1, 1292, 1095⟩,
  ⟨2003, .webVisit, 1427143490761166, 1, 1272, 1095⟩,
  ⟨2004, .webVisit, 1427143497831177, 1, 1293, 1095⟩,
  ⟨2005, .webVisit, 1427143497831177, 1, 1293, 1095⟩,
  ⟨2006, .webVisit, 1427143497831177, 1, 1293, 1095⟩,
  ⟨2007, .webVisit, 1427143499606181, 1, 1294, 1095⟩,
  ⟨2008, .webVisit, 1427143520940223, 1, 1295, 1095⟩,
  ⟨2009, .webVisit, 1427143520950223, 1, 1295, 1095⟩,
  ⟨2010, .webVisit, 1427143521062224, 1, 1296, 1095⟩,
  ⟨2011, .webVisit, 1427143522234000, 1, 1297, 1095⟩,
  ⟨2012, .webVisit, 1427143522234227, 1, 1297, 1095⟩,
  ⟨2013, .webVisit, 1427143522234227, 1, 1297, 1095⟩,
  ⟨2014, .webVisit, 1427143522377233, 1, 1293, 1095⟩,
  ⟨2015, .webVisit, 1427143523515237, 1, 1298, 1095⟩,
  ⟨2016, .webVisit, 1427143523525237, 1, 1299, 1095⟩,
  ⟨2017, .webVisit, 1427143524335239, 1, 1300, 1095⟩,
  ⟨2018, .webVisit, 1427143524365239, 1, 1301, 1095⟩,
  ⟨2019, .webVisit, 1427143530127000, 1, 1302, 1095⟩,
  ⟨2020, .webVisit, 1427143530127248, 1, 1302, 1095⟩,
  ⟨2021, .webVisit, 1427143530127248, 1, 1302, 1095⟩,
  ⟨2022, .webVisit, 1427143530137248, 1, 1302, 1095⟩,
  ⟨2023, .webVisit, 1427143532214751, 1, 1303, 1095⟩,
  ⟨2024, .webVisit, 1427143546289771, 1, 1297, 1095⟩,
  ⟨2025, .webVisit, 1427143548168785, 1, 1304, 1095⟩,
  ⟨2026, .webVisit, 1427143556728797, 1, 1305, 1095⟩,
  ⟨2027, .webVisit, 1427143556870799, 1, 1306, 1095⟩,
  ⟨2028, .webVisit, 1427143556870799, 1, 1307, 1095⟩,
  ⟨2029, .webVisit, 1427143557840802, 1, 1308, 1095⟩,
  ⟨2030, .webVisit, 1427143557850802, 1, 1309, 1095⟩,
  ⟨2031, .webVisit, 1427143558060802, 1, 1310, 1095⟩,
  ⟨2032, .webVisit, 1427144026618000, 1, 1311, 1095⟩,
  ⟨2033, .webVisit, 1427144026618464, 1, 1311, 1095⟩,
  ⟨2034, .webVisit, 1427144026618464, 1, 1311, 1095⟩ ]

def claim : Claim := .both (Sets.visited 1995) (.both (Sets.visited 1996) (.both (Sets.visited 1997) (.both (Sets.visited 1998) (.both (Sets.visited 1999) (.both (Sets.visited 2000) (.both (Sets.visited 2001) (.both (Sets.visited 2002) (.both (Sets.visited 2003) (.both (Sets.visited 2004) (.both (Sets.visited 2005) (.both (Sets.visited 2006) (.both (Sets.visited 2007) (.both (Sets.visited 2008) (.both (Sets.visited 2009) (.both (Sets.visited 2010) (.both (Sets.visited 2011) (.both (Sets.visited 2012) (.both (Sets.visited 2013) (.both (Sets.visited 2014) (.both (Sets.visited 2015) (.both (Sets.visited 2016) (.both (Sets.visited 2017) (.both (Sets.visited 2018) (.both (Sets.visited 2019) (.both (Sets.visited 2020) (.both (Sets.visited 2021) (.both (Sets.visited 2022) (.both (Sets.visited 2023) (.both (Sets.visited 2024) (.both (Sets.visited 2025) (.both (Sets.visited 2026) (.both (Sets.visited 2027) (.both (Sets.visited 2028) (.both (Sets.visited 2029) (.both (Sets.visited 2030) (.both (Sets.visited 2031) (.both (Sets.visited 2032) (.both (Sets.visited 2033) (Sets.visited 2034)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M270

#print axioms Cert.M270.verified
