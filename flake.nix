{
  description = "ESP32 club workshop: ESP-IDF 5.5 toolchain for the lab laptop";
  inputs.esp-dev.url = "github:mirrexagon/nixpkgs-esp-dev";
  outputs = { self, esp-dev }:
    let
      system = "x86_64-linux";
      pkgs = esp-dev.inputs.nixpkgs.legacyPackages.${system};
    in {
      # `nix develop`: idf.py + esptool for esp32 / s2 / s3 / c3 / c6.
      devShells.${system}.default = pkgs.mkShell {
        packages = [ esp-dev.packages.${system}.esp-idf-full pkgs.util-linux ];
      };
    };
}
