import ChainOfProof
open ChainOfProof

namespace Cert.M268

def cited : List Fact := [
  ⟨1915, .webVisit, 1427140099531147, 1, 1243, 881⟩,
  ⟨1916, .webVisit, 1427140106141776, 1, 1107, 881⟩,
  ⟨1917, .webVisit, 1427140106141776, 1, 1107, 881⟩,
  ⟨1918, .webVisit, 1427140509975902, 1, 1244, 881⟩,
  ⟨1919, .webVisit, 1427140509975902, 1, 1244, 881⟩,
  ⟨1920, .webVisit, 1427140517898270, 1, 1245, 881⟩,
  ⟨1921, .webVisit, 1427140517898270, 1, 1245, 881⟩,
  ⟨1922, .webVisit, 1427140518593045, 1, 1246, 881⟩,
  ⟨1923, .webVisit, 1427140518593045, 1, 1246, 881⟩,
  ⟨1924, .webVisit, 1427140528164615, 1, 1247, 881⟩,
  ⟨1925, .webVisit, 1427140528164615, 1, 1247, 881⟩,
  ⟨1926, .webVisit, 1427140534444477, 1, 1248, 881⟩,
  ⟨1927, .webVisit, 1427140534444477, 1, 1248, 881⟩,
  ⟨1928, .webVisit, 1427140534444477, 1, 1249, 881⟩,
  ⟨1929, .webVisit, 1427140534444477, 1, 1249, 881⟩,
  ⟨1930, .webVisit, 1427140534444477, 1, 1250, 881⟩,
  ⟨1931, .webVisit, 1427140534444477, 1, 1250, 881⟩,
  ⟨1932, .webVisit, 1427140534444477, 1, 1251, 881⟩,
  ⟨1933, .webVisit, 1427140534444477, 1, 1251, 881⟩,
  ⟨1934, .webVisit, 1427140535013159, 1, 1252, 881⟩,
  ⟨1935, .webVisit, 1427140535013159, 1, 1252, 881⟩,
  ⟨1936, .webVisit, 1427140535013159, 1, 1253, 881⟩,
  ⟨1937, .webVisit, 1427140535013159, 1, 1253, 881⟩,
  ⟨1938, .webVisit, 1427140535013159, 1, 1254, 881⟩,
  ⟨1939, .webVisit, 1427140535013159, 1, 1254, 881⟩,
  ⟨1940, .webVisit, 1427140535013159, 1, 1255, 881⟩,
  ⟨1941, .webVisit, 1427140535013159, 1, 1255, 881⟩,
  ⟨1942, .webVisit, 1427140564087329, 1, 1256, 881⟩,
  ⟨1943, .webVisit, 1427140564087329, 1, 1256, 881⟩,
  ⟨1944, .webVisit, 1427140568028965, 1, 1257, 881⟩,
  ⟨1945, .webVisit, 1427140568028965, 1, 1257, 881⟩,
  ⟨1946, .webVisit, 1427140568322083, 1, 1258, 881⟩,
  ⟨1947, .webVisit, 1427140568322083, 1, 1258, 881⟩,
  ⟨1948, .webVisit, 1427140575546476, 1, 1259, 881⟩,
  ⟨1949, .webVisit, 1427140575546476, 1, 1259, 881⟩,
  ⟨1950, .webVisit, 1427140579915469, 1, 1260, 881⟩,
  ⟨1951, .webVisit, 1427140579915469, 1, 1260, 881⟩,
  ⟨1952, .webVisit, 1427140588635952, 1, 1261, 881⟩,
  ⟨1953, .webVisit, 1427140588635952, 1, 1261, 881⟩,
  ⟨1954, .webVisit, 1427141093392629, 1, 1262, 1095⟩ ]

def claim : Claim := .both (Sets.visited 1915) (.both (Sets.visited 1916) (.both (Sets.visited 1917) (.both (Sets.visited 1918) (.both (Sets.visited 1919) (.both (Sets.visited 1920) (.both (Sets.visited 1921) (.both (Sets.visited 1922) (.both (Sets.visited 1923) (.both (Sets.visited 1924) (.both (Sets.visited 1925) (.both (Sets.visited 1926) (.both (Sets.visited 1927) (.both (Sets.visited 1928) (.both (Sets.visited 1929) (.both (Sets.visited 1930) (.both (Sets.visited 1931) (.both (Sets.visited 1932) (.both (Sets.visited 1933) (.both (Sets.visited 1934) (.both (Sets.visited 1935) (.both (Sets.visited 1936) (.both (Sets.visited 1937) (.both (Sets.visited 1938) (.both (Sets.visited 1939) (.both (Sets.visited 1940) (.both (Sets.visited 1941) (.both (Sets.visited 1942) (.both (Sets.visited 1943) (.both (Sets.visited 1944) (.both (Sets.visited 1945) (.both (Sets.visited 1946) (.both (Sets.visited 1947) (.both (Sets.visited 1948) (.both (Sets.visited 1949) (.both (Sets.visited 1950) (.both (Sets.visited 1951) (.both (Sets.visited 1952) (.both (Sets.visited 1953) (Sets.visited 1954)))))))))))))))))))))))))))))))))))))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M268

#print axioms Cert.M268.verified
