// Uses unmodified Frosty 1.0.6.3 readers. No game write APIs are called.
using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Reflection;
using System.Collections.Generic;
using System.Web.Script.Serialization;
using FrostySdk;
using FrostySdk.Managers;
using FrostySdk.Interfaces;
using FsLocalizationPlugin;
using FrostySdk.Resources;
using Frosty.Core;
using Frosty.Core.IO;
using Frosty.Core.Mod;
using FrostySdk.IO;
using FrostySdk.Ebx;
using System.Threading;

public class CatalystBackend {
    public class Row {public string id {get;set;} public string text {get;set;}}
    public class ExportDoc {public List<Row> entries {get;set;}}
    static string tools;
    class Logger : ILogger {
        public void Log(string s, params object[] v) { if(!s.StartsWith("progress:")) Console.WriteLine(s,v); }
        public void LogWarning(string s, params object[] v) { Console.WriteLine("WARN: "+s,v); }
        public void LogError(string s, params object[] v) { Console.WriteLine("ERROR: "+s,v); }
    }
    static Assembly Resolve(object sender, ResolveEventArgs e) {
        string n=new AssemblyName(e.Name).Name;
        string p=n=="EbxClasses" ? Path.Combine(tools,"Profiles",ProfilesLibrary.SDKFilename+".dll") : Path.Combine(tools,n+".dll");
        if (!File.Exists(p)) p=Path.Combine(tools,"Plugins",n+".dll");
        if (!File.Exists(p)) p=Path.Combine(tools,"ThirdParty",n+".dll");
        return File.Exists(p) ? Assembly.LoadFile(p) : null;
    }
    static void Json(string p, object x) {
        var j=new JavaScriptSerializer(); j.MaxJsonLength=int.MaxValue;
        File.WriteAllText(p,j.Serialize(x),new UTF8Encoding(false,true));
    }
    static void BuildMod(AssetManager am, EbxAssetEntry entry, byte[] binaryData, byte[] histogramData, string directory, string fontPath) {
        Directory.CreateDirectory(directory);
        var ebx=am.GetEbx(entry);
        object root=ebx.RootObject;
        var props=root.GetType().GetProperties();
        Json(Path.Combine(directory,"localization_ebx_fields.json"),props.Select(p=>new {name=p.Name,type=p.PropertyType.FullName}).ToArray());
        var binarySize=props.Single(p=>p.Name=="BinaryChunkSize");
        var histogramSize=props.Single(p=>p.Name=="HistogramChunkSize");
        object oldBinarySize=binarySize.GetValue(root,null),oldHistogramSize=histogramSize.GetValue(root,null);
        binarySize.SetValue(root,Convert.ChangeType(binaryData.Length,binarySize.PropertyType),null);
        histogramSize.SetValue(root,Convert.ChangeType(histogramData.Length,histogramSize.PropertyType),null);
        dynamic obj=root;
        Guid binary=obj.BinaryChunk,histogram=obj.HistogramChunk;
        am.ModifyEbx(entry.Name,ebx);
        foreach(var pair in new []{new {id=binary,data=binaryData},new {id=histogram,data=histogramData}}) {
            var chunk=am.GetChunkEntry(pair.id);
            chunk.ModifiedEntry.OriginalSize=pair.data.Length;
            chunk.ModifiedEntry.H32=chunk.H32;
            chunk.ModifiedEntry.FirstMip=chunk.FirstMip;
            entry.LinkAsset(chunk);
        }
        byte[] fontData=File.ReadAllBytes(fontPath);
        var fontRes=am.GetResEntry(0x9AA46CCB815CD1C5UL);
        if(fontRes==null || fontRes.ResType!=(uint)ResourceType.UITtfFontFile) throw new Exception("Unexpected font resource");
        if(fontData.Length<12 || fontData[0]!=0 || fontData[1]!=1 || fontData[2]!=0 || fontData[3]!=0) throw new Exception("Not a TrueType font");
        am.ModifyRes(fontRes.ResRid,fontData,fontRes.ResMeta);
        var fontEbx=am.GetEbxEntry("UI/Fonts/FontSources/ARHeitiMediumB5_TC");
        fontEbx.LinkAsset(fontRes);
        // Standard EBX and chunk records; do not invoke the stock localization encoder.
        // A normal PluginManager with no plugin folder has initialized empty handler dictionaries.
        string writerContext=Path.Combine(directory,"writer_context");Directory.CreateDirectory(writerContext);
        string savedDirectory=Environment.CurrentDirectory;
        Environment.CurrentDirectory=writerContext;
        Frosty.Core.App.PluginManager=new PluginManager(Frosty.Core.App.Logger,PluginManagerType.Editor);
        Environment.CurrentDirectory=savedDirectory;
        string configPath=Path.Combine(writerContext,"isolated_build_config.json");
        File.WriteAllText(configPath,"{}",new UTF8Encoding(false));
        Config.Load(configPath);
        var settings=new ModSettings {Title="Mirror's Edge Catalyst Simplified Chinese - AUTOMATIC BUILD",Author="Local conversion",Category="Localization",Version="0.4.0-auto-test",Description="Official TraditionalChinese text converted locally with OpenCC tw2sp. Expanded histogram. All Han glyphs unified to OFL Noto Sans SC Regular (weight 400). Original non-Han glyphs and UI settings preserved. Offline coverage verified; this version needs in-game visual validation. Select TraditionalChinese in game. Raw resource replacement; do not combine with other zh text mods."};
        var project=new FrostyProject();
        project.ModSettings.Title=settings.Title;project.ModSettings.Author=settings.Author;project.ModSettings.Category=settings.Category;project.ModSettings.Version=settings.Version;project.ModSettings.Description=settings.Description;
        string modPath=Path.Combine(directory,"MEC_SimplifiedChinese_AUTO_TEST.fbmod");
        using(var writer=new FrostyModWriter(new FileStream(modPath,FileMode.Create),settings)) writer.WriteProject(project,false,CancellationToken.None);
        string projectPath=Path.Combine(directory,"MEC_SimplifiedChinese_AUTO_TEST.fbproject");
        project.Save(projectPath,false);
        var checks=new List<object>();
        bool payloadsExact=true,ebxFieldsExact=false;
        using(var reader=new FrostyModReader(new FileStream(modPath,FileMode.Open,FileAccess.Read))) {
            if(!reader.IsValid || reader.GameVersion!=Frosty.Core.App.FileSystem.Head) throw new Exception("MOD header/profile/version check failed");
            var details=reader.ReadModDetails();
            var resources=reader.ReadResources();
            if(resources.Count(r=>r.Type==ModResourceType.Ebx)!=1 || resources.Count(r=>r.Type==ModResourceType.Chunk)!=2 || resources.Count(r=>r.Type==ModResourceType.Res)!=1) throw new Exception("Unexpected mod resources");
            foreach(var resource in resources.Where(r=>r.IsModified)) {
                byte[] compressed=reader.GetResourceData(resource);
                if(resource.HasHandler) throw new Exception("Unexpected custom handler");
                if(!FrostySdk.Utils.GenerateSha1(compressed).Equals(resource.Sha1)) throw new Exception("MOD resource hash failed");
                byte[] unpacked;
                using(var cas=new CasReader(new MemoryStream(compressed))) unpacked=cas.Read();
                bool matches=false;
                if(resource.Type==ModResourceType.Chunk) {
                    var id=Guid.Parse(resource.Name);
                    matches=id==binary ? unpacked.SequenceEqual(binaryData) : id==histogram && unpacked.SequenceEqual(histogramData);
                } else if(resource.Type==ModResourceType.Res) {
                    var resRecord=new ResAssetEntry();resource.FillAssetEntry(resRecord);
                    matches=resource.Name.Equals(fontRes.Name,StringComparison.OrdinalIgnoreCase) && unpacked.SequenceEqual(fontData) && resRecord.ResRid==fontRes.ResRid && resRecord.ResType==fontRes.ResType && resRecord.ResMeta.SequenceEqual(fontRes.ResMeta);
                } else if(resource.Type==ModResourceType.Ebx) {
                    using(var er=EbxReader.CreateReader(new MemoryStream(unpacked),Frosty.Core.App.FileSystem)) {
                        dynamic decoded=er.ReadAsset<EbxAsset>().RootObject;
                        matches=resource.Name.Equals(entry.Name,StringComparison.OrdinalIgnoreCase) && (Guid)decoded.BinaryChunk==binary && (Guid)decoded.HistogramChunk==histogram && Convert.ToInt64(decoded.BinaryChunkSize)==binaryData.Length && Convert.ToInt64(decoded.HistogramChunkSize)==histogramData.Length && decoded.Language.ToString()=="LanguageFormat_TraditionalChinese";
                        ebxFieldsExact=matches;
                    }
                }
                payloadsExact &= matches;
                checks.Add(new {name=resource.Name,type=resource.Type.ToString(),size=unpacked.Length,sha1_verified=true,has_custom_handler=resource.HasHandler,payload_matches=matches});
            }
        }
        if(!payloadsExact || !ebxFieldsExact) throw new Exception("Packaged resource verification failed");
        Json(Path.Combine(directory,"mod_build_report.json"),new {fbmod=modPath,fbproject=projectPath,frosty_version="1.0.6.3",profile=ProfilesLibrary.ProfileName,game_head=Frosty.Core.App.FileSystem.Head,old_binary_size=oldBinarySize,new_binary_size=binaryData.Length,old_histogram_size=oldHistogramSize,new_histogram_size=histogramData.Length,resources=checks,mod_structure_valid=true,ebx_chunk_size_links_valid=true,compressed_payloads_verified=true,font_coverage_verified=true,font_resource_payload_verified=true,in_game_tested=false,installed=false,game_files_modified=false});
        Console.WriteLine("TEST fbmod built and read back: "+modPath);
    }

    static byte[] Chunk(AssetManager am, ChunkAssetEntry e) {
        using(var s=am.GetChunk(e)) using(var m=new MemoryStream()) {s.CopyTo(m);return m.ToArray();}
    }
    // The official decoder supplies every text. Read only its documented, verified
    // ID table to retain duplicate rows; do not implement a container/text decoder.
    static List<Row> DecodeRows(AssetManager am, ChunkAssetEntry bin, ChunkAssetEntry hist) {
        var db=new FsLocalizationStringDatabase();
        var method=typeof(FsLocalizationStringDatabase).GetMethod("AddResource",BindingFlags.NonPublic|BindingFlags.Instance);
        if(method==null) throw new Exception("Unsupported localization plugin API");
        method.Invoke(db,new object[]{bin,hist});
        var texts=(Dictionary<uint,string>)typeof(FsLocalizationStringDatabase).GetField("strings",BindingFlags.NonPublic|BindingFlags.Instance).GetValue(db);
        var rows=new List<Row>();
        byte[] data=Chunk(am,bin);
        using(var r=new NativeReader(new MemoryStream(data))) {
            if(r.ReadUInt()!=0x39000) throw new Exception("Unsupported string table magic");
            r.ReadUInt(); int count=r.ReadInt(); uint start=r.ReadUInt(),end=r.ReadUInt();
            if(count<=0 || start+8L>data.Length || end+8L>data.Length || end-start!=count*8L)
                throw new Exception("Invalid string table bounds/count");
            r.Position=start+8L;
            for(int i=0;i<count;i++) {
                uint id=r.ReadUInt(),offset=r.ReadUInt();
                if(end+offset+8L>=data.Length || !texts.ContainsKey(id)) throw new Exception("Invalid ID/offset");
                rows.Add(new Row {id=id.ToString("X8"),text=texts[id]});
            }
        }
        return rows;
    }
    public static int Main(string[] args) {
        Console.OutputEncoding=new UTF8Encoding(false);
        try {tools=Path.GetFullPath(args[0]);AppDomain.CurrentDomain.AssemblyResolve+=Resolve;return Run(args);}
        catch(Exception e) {Console.WriteLine(e.ToString());return 1;}
    }
    static int Run(string[] args) {
        string game=Path.GetFullPath(args[1]),output=Path.GetFullPath(args[2]);
        string gamePrefix=game.TrimEnd(Path.DirectorySeparatorChar)+Path.DirectorySeparatorChar;
        foreach(string p in new[]{output,tools})
            if(p.Equals(game,StringComparison.OrdinalIgnoreCase) || p.StartsWith(gamePrefix,StringComparison.OrdinalIgnoreCase))
                throw new Exception("All working paths must be outside game");
        Directory.CreateDirectory(output); Environment.CurrentDirectory=tools;
        ProfilesLibrary.Initialize(new List<Profile>()); ProfilesLibrary.Initialize("MirrorsEdgeCatalyst");
        if(ProfilesLibrary.DataVersion!=20160607 || ProfilesLibrary.RequiresKey) throw new Exception("Unsupported profile");
        var logger=new Logger();var fs=new FileSystem(game);
        foreach(var s in ProfilesLibrary.Sources) fs.AddSource(s.Path,s.SubDirs);
        fs.Initialize();
        if(fs.Head!=175205) throw new Exception("Game head differs from verified Catalyst adapter; inspect before updating");
        var rm=new ResourceManager(fs);rm.SetLogger(logger);rm.Initialize();TypeLibrary.Initialize();
        var am=new AssetManager(fs,rm);am.SetLogger(logger);am.Initialize(true);
        Frosty.Core.App.AssetManager=am;Frosty.Core.App.ResourceManager=rm;Frosty.Core.App.FileSystem=fs;Frosty.Core.App.Logger=logger;
        var candidates=am.EnumerateEbx().Where(e=>e.Type=="FsUITextDatabase").Where(e=>am.GetEbx(e).RootObject.GetType().GetProperty("Language").GetValue(am.GetEbx(e).RootObject,null).ToString()=="LanguageFormat_TraditionalChinese").ToList();
        if(candidates.Count!=1) throw new Exception("Expected one Traditional Chinese database");
        var entry=candidates[0];dynamic asset=am.GetEbx(entry).RootObject;
        if(!entry.Name.Equals("Localization/fs_zh_loc",StringComparison.OrdinalIgnoreCase)) throw new Exception("Unexpected localization resource");
        Guid bin=asset.BinaryChunk,hist=asset.HistogramChunk;
        var be=am.GetChunkEntry(bin);var he=am.GetChunkEntry(hist);
        var originalRows=DecodeRows(am,be,he);
        if(originalRows.Count!=7978 || originalRows.Select(r=>r.id).Distinct().Count()!=7977) throw new Exception("Source corpus changed; inspect before updating");
        Json(Path.Combine(output,"all_rows.json"),new {schema_version=1,metadata=new {language="TraditionalChinese",lossless=true,id_format="hex32",source_role="game_export",encoding="Frostbite histogram; UTF-8 JSON",resource=entry.Name,resource_guid=entry.Guid.ToString(),binary_chunk=bin.ToString(),histogram_chunk=hist.ToString(),game_head=fs.Head},entries=originalRows});
        File.WriteAllBytes(Path.Combine(output,"binary.chunk"),Chunk(am,be));
        File.WriteAllBytes(Path.Combine(output,"histogram.chunk"),Chunk(am,he));
        var fe=am.GetEbxEntry("UI/Fonts/FontSources/ARHeitiMediumB5_TC");
        if(fe==null || fe.Type!="UITtfAsset") throw new Exception("Unexpected font EBX");
        var font=am.GetResEntry(0x9AA46CCB815CD1C5UL);
        if(font==null || font.ResType!=(uint)ResourceType.UITtfFontFile) throw new Exception("Unexpected font resource");
        // Verify actual EBX binding, rather than assuming RID solely from a prior case.
        dynamic fontRoot=am.GetEbx(fe).RootObject;
        if((ulong)fontRoot.FontResource!=font.ResRid) throw new Exception("Font binding changed");
        using(var src=am.GetRes(font)) using(var dst=File.Create(Path.Combine(output,"original_font.ttf"))) src.CopyTo(dst);
        Json(Path.Combine(output,"resource_manifest.json"),new {profile=ProfilesLibrary.ProfileName,head=fs.Head,rows=originalRows.Count,font_ebx=fe.Name,font_rid=font.ResRid.ToString("X16"),game_written=false});
        Console.WriteLine("Exported "+originalRows.Count+" rows and bound font");
        if(args.Length==3) return 0;
        if(args.Length!=7) throw new Exception("Expected export args or complete build args");
        foreach(string p in new[]{Path.GetFullPath(args[4]),Path.GetFullPath(args[5])})
            if(p.Equals(game,StringComparison.OrdinalIgnoreCase)||p.StartsWith(gamePrefix,StringComparison.OrdinalIgnoreCase)) throw new Exception("Refusing output inside game");
        var js=new JavaScriptSerializer();js.MaxJsonLength=int.MaxValue;
        var expected=js.Deserialize<ExportDoc>(File.ReadAllText(args[3],Encoding.UTF8));
        if(!originalRows.Select(r=>r.id).SequenceEqual(expected.entries.Select(r=>r.id))) throw new Exception("Target ID sequence differs");
        byte[] binary=File.ReadAllBytes(Path.Combine(args[4],"simplified_binary.chunk"));
        byte[] histogram=File.ReadAllBytes(Path.Combine(args[4],"expanded_histogram.chunk"));
        if(!am.ModifyChunk(bin,binary)||!am.ModifyChunk(hist,histogram)) throw new Exception("Memory import failed");
        var decoded=DecodeRows(am,be,he);
        bool exact=decoded.Count==expected.entries.Count&&decoded.Zip(expected.entries,(a,b)=>a.id==b.id&&a.text==b.text).All(x=>x);
        Json(Path.Combine(args[4],"frosty_sdk_crosscheck.json"),new {decoded_rows=decoded.Count,all_ids_texts_order_duplicate_rows_exact=exact,game_written=false});
        if(!exact) throw new Exception("Official SDK crosscheck failed");
        BuildMod(am,entry,binary,histogram,Path.GetFullPath(args[5]),Path.GetFullPath(args[6]));return 0;
    }
}

