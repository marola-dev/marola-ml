{
  description = "marola-ml — marola's offline Python: DSPy compile, fine-tune, marola-sea, the benchmark gate (MIP-0070)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    # Tools, the just module and the lint toolchain. Bump with .github/workflows/*.yml's @tag.
    marola-devkit = {
      url = "github:marola-dev/marola-devkit/v0.8.0";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    # setup-ml-venv / setup-cuda-cache / python-cuda: the CUDA torch venv marola-sea trains in.
    cuda = {
      url = "github:h0ffmann/nix-config/labs/cuda?dir=labs/cuda";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, flake-utils, marola-devkit, cuda }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        devkit = marola-devkit.lib.${system};
      in
      {
        # Docker is the host's, as in every marola repo: `just benchmark` runs the pinned app image.
        # pdoc is `just api-docs`'s generator (MIP-0074 §5.2), not part of devkit.tools' python.
        devShells.default = pkgs.mkShell {
          name = "marola-ml";
          packages = [ pkgs.ollama pkgs.python3Packages.pdoc ]
            ++ devkit.tools
            ++ pkgs.lib.optionals (system == "x86_64-linux") cuda.lib.${system}.tools;
          shellHook = devkit.shellHook + ''
            git config core.hooksPath .devkit/.githooks 2>/dev/null || true
            echo "marola-ml dev shell. Run 'just' to see available commands."
          '';
        };
      });
}
