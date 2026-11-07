Name:		apache-commons-jxpath
Version:	1.4.0
Release:	1
Summary:	XPath interpreter for Java object graphs
Group:		Development/Java
License:	ASL 2.0
URL:		https://commons.apache.org/proper/commons-jxpath/
Source0:	https://github.com/apache/commons-jxpath/archive/refs/tags/rel/commons-jxpath-%{version}.tar.gz#/commons-jxpath-%{version}.tar.gz

BuildArch:	noarch
BuildRequires:	python
BuildRequires:	mvn(org.apache.commons:commons-parent:pom::)
BuildRequires:	mvn(org.apache:apache:pom::)
BuildRequires:	mvn(commons-beanutils:commons-beanutils)
# Literal, so the first rpmbuild -bs records them before sysjar is installed.
BuildRequires:	maven
BuildRequires:	java-current-devel
BuildSystem:	maven
BuildOption(install):	--file-name commons-jxpath --link %{name} --alias org.apache.commons:commons-jxpath

Provides:	jakarta-commons-jxpath = 0:%{version}-%{release}
Obsoletes:	jakarta-commons-jxpath < 0:%{version}-%{release}
Obsoletes:	%{name}-javadoc < %{version}-%{release}
Obsoletes:	jakarta-commons-jxpath-javadoc < 0:%{version}-%{release}

%description
Apache Commons JXPath applies XPath expressions to JavaBeans, maps,
DOM, and other object graphs. 1.4.0 adds the ends-with function and
fixes empty documents, indexed sets, LazyDynaBean, and concurrent use
of the context factory and function library. Java 8 is required. Tests
are skipped. JDOM and servlet contexts are omitted because those
libraries are not packaged. Commons BeanUtils is required. The
automatic module name is org.apache.commons.jxpath.

%prep
%autosetup -n commons-jxpath-rel-commons-jxpath-%{version}
# JDOM and the servlet API are loaded by name and are not packaged.
# BeanUtils is a real import, so it stays and is no longer optional.
# The jacoco profile activates from a marker file and is not used.
python - <<'PY'
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

shutil.rmtree("src/main/java/org/apache/commons/jxpath/ri/model/jdom")
shutil.rmtree("src/main/java/org/apache/commons/jxpath/servlet")
Path("src/main/java/org/apache/commons/jxpath/xml/JDOMParser.java").unlink()
Path("src/site/resources/profile.jacoco").unlink()

ET.register_namespace("", "http://maven.apache.org/POM/4.0.0")
ET.register_namespace("xsi", "http://www.w3.org/2001/XMLSchema-instance")

def local(tag):
    return tag.rsplit("}", 1)[-1]

drop_artifacts = {"servlet-api", "jsp-api", "jdom"}
path = Path("pom.xml")
tree = ET.parse(path)
root = tree.getroot()
removed = []
for parent in list(root.iter()):
    if local(parent.tag) != "dependencies":
        continue
    for child in list(parent):
        if local(child.tag) != "dependency":
            continue
        scope = artifact = ""
        for item in child:
            name = local(item.tag)
            if name == "scope":
                scope = (item.text or "").strip()
            elif name == "artifactId":
                artifact = (item.text or "").strip()
        if scope == "test" or artifact in drop_artifacts:
            parent.remove(child)
            removed.append(artifact)
expected = {
    "servlet-api",
    "jsp-api",
    "jdom",
    "junit-jupiter-engine",
    "mockrunner-jdk1.3-j2ee1.3",
    "commons-lang3",
    "commons-io",
}
if set(removed) != expected:
    raise SystemExit("unexpected dependency edit: " + " ".join(sorted(removed)))
bean = None
for parent in root.iter():
    if local(parent.tag) != "dependency":
        continue
    artifact = ""
    for item in parent:
        if local(item.tag) == "artifactId":
            artifact = (item.text or "").strip()
    if artifact == "commons-beanutils":
        bean = parent
if bean is None:
    raise SystemExit("beanutils dependency missing")
for item in list(bean):
    if local(item.tag) == "optional":
        bean.remove(item)
tree.write(path, encoding="UTF-8", xml_declaration=True)
text = path.read_text(encoding="utf-8")
for needle in (
    "<artifactId>servlet-api</artifactId>",
    "<artifactId>jsp-api</artifactId>",
    "<artifactId>jdom</artifactId>",
    "<scope>test</scope>",
    "<optional>",
):
    if needle in text:
        raise SystemExit("pom still contains " + needle)
if "commons-beanutils" not in text:
    raise SystemExit("beanutils was removed")
for java in Path("src/main/java").rglob("*.java"):
    for line in java.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("import ") and ("org.jdom" in stripped or "javax.servlet" in stripped):
            raise SystemExit("import remains in " + str(java))
PY

%build -a
cat > manifest-addition <<'EOF'
Automatic-Module-Name: org.apache.commons.jxpath
EOF
jar ufm target/commons-jxpath-%{version}.jar manifest-addition
java --module-path target/commons-jxpath-%{version}.jar --describe-module org.apache.commons.jxpath | grep -q '^org.apache.commons.jxpath'

%files -f .mfiles
%doc LICENSE.txt NOTICE.txt RELEASE-NOTES.txt README.md
