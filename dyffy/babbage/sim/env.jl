# Call getenv function from libc to get environment variable
function getenv(var::String)
    val = ccall((:getenv, "libc"),
                Ptr{Uint8}, (Ptr{Uint8},), bytestring(var))
    if val == C_NULL
        error("getenv: undefined variable: ", var)
    end
    bytestring(val)
end

function gethostname()
    hostname = Array(Uint8, 128)
    ccall((:gethostname, "libc"), Int32,
          (Ptr{Uint8}, Uint),
          hostname, length(hostname))
    return bytestring(convert(Ptr{Uint8}, hostname))
end
