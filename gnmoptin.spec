%define name portal-gnmoptin
%define version 1.0
%define unmangled_version 1.0
%define release 1

Summary: Opt-Ins Plugin
Name: %{name}
Version: %{version}
Release: %{release}
License: Internal GNM software
Source0: gnmoptin.tar.gz
Group: Applications/Productivity
#BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
BuildRoot: %{_tmppath}/gnmoptin
Prefix: %{_prefix}
BuildArch: noarch
Vendor: David Allison <david.allison@theguardian.com> and Andy Gallagher <andy.gallagher@theguardian.com>
Requires: Portal portal-fontawesome >= 4.7.0-1

%description
Allows users to opt in and out of optional features

%prep

%build

%install
mkdir -p $RPM_BUILD_ROOT/opt/cantemo/portal/portal/plugins/gnmoptin
cp -a /opt/cantemo/portal/portal/plugins/gnmoptin/* $RPM_BUILD_ROOT/opt/cantemo/portal/portal/plugins/gnmoptin

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root)
/opt/cantemo/portal/portal/plugins/gnmoptin

%post
/opt/cantemo/portal/manage.py migrate gnmoptin

%preun
