import ChainOfProof
open ChainOfProof

namespace Cert.M269

def cited : List Fact := [
  ⟨1955, .webVisit, 1427141093392629, 1, 1262, 1095⟩,
  ⟨1956, .webVisit, 1427141093408229, 1, 1262, 1095⟩,
  ⟨1957, .webVisit, 1427142413986000, 1, 1263, 1095⟩,
  ⟨1958, .webVisit, 1427142413986593, 1, 1263, 1095⟩,
  ⟨1959, .webVisit, 1427142421819000, 1, 1264, 1095⟩,
  ⟨1960, .webVisit, 1427142421819807, 1, 1264, 1095⟩,
  ⟨1961, .webVisit, 1427142453345000, 1, 1265, 1095⟩,
  ⟨1962, .webVisit, 1427142453345068, 1, 1265, 1095⟩,
  ⟨1963, .webVisit, 1427142459759000, 1, 1266, 1095⟩,
  ⟨1964, .webVisit, 1427142459759679, 1, 1266, 1095⟩,
  ⟨1965, .webVisit, 1427142869099416, 1, 1267, 1095⟩,
  ⟨1966, .webVisit, 1427142869239816, 1, 1268, 1095⟩,
  ⟨1967, .webVisit, 1427143420782124, 1, 1107, 881⟩,
  ⟨1968, .webVisit, 1427143420782124, 1, 1107, 881⟩,
  ⟨1969, .webVisit, 1427143427512000, 1, 1269, 1095⟩,
  ⟨1970, .webVisit, 1427143427512480, 1, 1269, 1095⟩,
  ⟨1971, .webVisit, 1427143427512480, 1, 1269, 1095⟩,
  ⟨1972, .webVisit, 1427143428413885, 1, 1270, 1095⟩,
  ⟨1973, .webVisit, 1427143430689493, 1, 1271, 1095⟩,
  ⟨1974, .webVisit, 1427143432457000, 1, 1272, 1095⟩,
  ⟨1975, .webVisit, 1427143432457705, 1, 1272, 1095⟩,
  ⟨1976, .webVisit, 1427143432457705, 1, 1272, 1095⟩,
  ⟨1977, .webVisit, 1427143432477705, 1, 1269, 1095⟩,
  ⟨1978, .webVisit, 1427143434679711, 1, 1273, 1095⟩,
  ⟨1979, .webVisit, 1427143464920858, 1, 1274, 1095⟩,
  ⟨1980, .webVisit, 1427143465070860, 1, 1275, 1095⟩,
  ⟨1981, .webVisit, 1427143465115362, 1, 1276, 1095⟩,
  ⟨1982, .webVisit, 1427143465732871, 1, 1277, 1095⟩,
  ⟨1983, .webVisit, 1427143465805372, 1, 1278, 1095⟩,
  ⟨1984, .webVisit, 1427143466060376, 1, 1279, 1095⟩,
  ⟨1985, .webVisit, 1427143466087877, 1, 1280, 1095⟩,
  ⟨1986, .webVisit, 1427143466579888, 1, 1281, 1095⟩,
  ⟨1987, .webVisit, 1427143467279400, 1, 1282, 1095⟩,
  ⟨1988, .webVisit, 1427143467646905, 1, 1283, 1095⟩,
  ⟨1989, .webVisit, 1427143467944410, 1, 1284, 1095⟩,
  ⟨1990, .webVisit, 1427143467946910, 1, 1284, 1095⟩,
  ⟨1991, .webVisit, 1427143467994912, 1, 1285, 1095⟩,
  ⟨1992, .webVisit, 1427143468002912, 1, 1286, 1095⟩,
  ⟨1993, .webVisit, 1427143468186415, 1, 1287, 1095⟩,
  ⟨1994, .webVisit, 1427143468188916, 1, 1287, 1095⟩ ]

def claim : Claim := .both (Sets.visited 1955) (.both (Sets.visited 1956) (.both (Sets.visited 1957) (.both (Sets.visited 1958) (.both (Sets.visited 1959) (.both (Sets.visited 1960) (.both (Sets.visited 1961) (.both (Sets.visited 1962) (.both (Sets.visited 1963) (.both (Sets.visited 1964) (.both (Sets.visited 1965) (.both (Sets.visited 1966) (.both (Sets.visited 1967) (.both (Sets.visited 1968) (.both (Sets.visited 1969) (.both (Sets.visited 1970) (.both (Sets.visited 1971) (.both (Sets.visited 1972) (.both (Sets.visited 1973) (.both (Sets.visited 1974) (.both (Sets.visited 1975) (.both (Sets.visited 1976) (.both (Sets.visited 1977) (.both (Sets.visited 1978) (.both (Sets.visited 1979) (.both (Sets.visited 1980) (.both (Sets.visited 1981) (.both (Sets.visited 1982) (.both (Sets.visited 1983) (.both (Sets.visited 1984) (.both (Sets.visited 1985) (.both (Sets.visited 1986) (.both (Sets.visited 1987) (.both (Sets.visited 1988) (.both (Sets.visited 1989) (.both (Sets.visited 1990) (.both (Sets.visited 1991) (.both (Sets.visited 1992) (.both (Sets.visited 1993) (Sets.visited 1994)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M269

#print axioms Cert.M269.verified
