{ pkgs ? import <nixpkgs> {} }:
pkgs.mkShell {
    nativeBuildInputs = with pkgs.buildPackages;
    let
      custom = import (builtins.fetchTarball https://github.com/nixos/nixpkgs/tarball/f044a8cde2d5c01d36e3a9cf63a48824a89461b5) {};
    in
    [
      custom.earthly # 0.7.23 because of https://github.com/earthly/earthly/issues/4265
    ];
}