#!/home/notal/anaconda3/bin/python3
import os
import Bio.SeqIO
import Bio.Entrez
import Bio.SeqRecord
import Bio.Seq
import runbin
import random
import colorama


def QtoA(inputfile, outputfile, Ltrim=0, trim=0):
    seqs = []  # Bio.SeqIO.read(inputfile, "fastq")
    print(f'Reading ' + colorama.Fore.YELLOW + f'{inputfile}' + colorama.Style.RESET_ALL)
    for record in Bio.SeqIO.parse(inputfile, "fastq"):
        if trim:  # if trimming is indicated
            trimmed = record.seq[Ltrim:trim]  # trim record to indicated range
            record.letter_annotations = {}  # empty letter annotations so they can match seq length
            record.seq = trimmed  # reasign record.seq to newly trimmed sequence
        print(
            colorama.Fore.BLUE + f'{record.seq[:20]}...{record.seq[-20:]} ' + colorama.Style.RESET_ALL +
            f' sequnce number ' + colorama.Fore.GREEN + f'{len(seqs):,}' + colorama.Style.RESET_ALL,
            end="\r")
        seqs.append(record)
    print(f'writing ' + colorama.Fore.YELLOW + f'{outputfile}' + colorama.Style.RESET_ALL)
    Bio.SeqIO.write(seqs, outputfile, "fasta")  # "./inprocess/"+
    return seqs


def merge_pairs(in1, in2, out, bbmerge_location='./bins/bbmap/bbmerge-auto.sh'):
    message = []
    bbmerge_command = bbmerge_location
    if '.gz' in in1:
        merge_out = in1.split('.fastq.gz')[0]+'_merge.fastq'
        unmerge_out1 = in1.split('.fastq.gz')[0]+'_unmerge.fastq'
        unmerge_out2 = in2.split('.fastq.gz')[0]+'_unmerge.fastq'
    else:
        merge_out = os.path.splitext(in1)[0]+'_merge'+os.path.splitext(in1)[1]
        unmerge_out1 = os.path.splitext(in1)[0]+'_unmerge'+os.path.splitext(in1)[1]
        unmerge_out2 = os.path.splitext(in2)[0]+'_unmerge'+os.path.splitext(in2)[1]
    for file in [out, merge_out, unmerge_out1, unmerge_out2]:
        if os.path.exists(file):
            os.remove(file)
    bbmerge_command += f' in1={in1} in2={in2} out={merge_out} outu1={unmerge_out1} outu2={unmerge_out2}'
    print(f'{bbmerge_command}')
    bbmerge = runbin.Command(bbmerge_command)
    run = bbmerge.run(timeout=20000)
    print(run[1].decode())
    print(run[2].decode())
    filenames = [merge_out, unmerge_out1, unmerge_out2]
    os.system('cat ' + ' '.join(filenames) + ' > ' + out)
    #with open(out, 'w') as outfile:
    #    for fname in filenames:
    #        with open(fname) as infile:
    #            for line in infile:
    #                outfile.write(line)
    for tempfile in [merge_out, unmerge_out1, unmerge_out2]:
        os.remove(tempfile)


def Trim(inputfile, outputfile, barcode5, primer5='GGGTTCCGCCGGATGGC', primer3='CCTAACTGCTGTGCCACT', trim3=16, trim5=21,
         minlen=10, filetype='fastq', paired=None, pairedoutputfile=None, cutadaptlocation='cutadapt'):
    if not pairedoutputfile:
        pairedoutputfile = f'{outputfile}.pairs'
    message = []
    cutcommand = []
    tempfiles = []
    if trim3 > 0 or trim5 > 0:
        cutcommand.append(
            f'{cutadaptlocation} -a ^{barcode5}{primer5}...{primer3} -j 0 --discard-untrimmed '
            f'-o ./inprocess/temptrimmed.{filetype} ./{inputfile} --report minimal')
        tempfiles.append(f'./inprocess/temptrimmed.{filetype}')
        if trim3 > 0 and trim5 > 0:  # both trim3 and 5
            cutcommand.append(
                f'{cutadaptlocation} -u -{trim3} -j 0 -o ./inprocess/temptrimmed1.{filetype} '
                f'./inprocess/temptrimmed.{filetype} --report minimal')
            cutcommand.append(
                f'{cutadaptlocation} -u {trim5} -j 0 -m {minlen} -o {outputfile} ./inprocess/temptrimmed1.{filetype} '
                f'--report minimal')
            tempfiles.append(f'./inprocess/temptrimmed1.{filetype}')
        elif trim3 > 0:  # only trim3
            cutcommand.append(
                f'{cutadaptlocation} -u -{trim3} -j 0 -m {minlen} -o {outputfile}  ./inprocess/temptrimmed.{filetype} '
                f'--report minimal')
        else:  # only trim5
            cutcommand.append(
                f'{cutadaptlocation} -u {trim5} -j 0 -m {minlen} -o {outputfile} ./inprocess/temptrimmed1.{filetype} '
                f'--report minimal')
    elif len(primer3) > 0 or len(primer5) > 0 or len(barcode5) > 0:
        if len(primer3) > 0:
            if len(primer5) + len(barcode5) > 0:
                cutcommand.append(
                    f'{cutadaptlocation} -a {barcode5}{primer5}...{primer3} -j 0 -m {minlen} --discard-untrimmed '
                    f'--revcomp -O 17 -o {outputfile} {inputfile} --report minimal')
            else:
                cutcommand.append(
                    f'{cutadaptlocation} -a {primer3} -j 0 -O 17 -m {minlen} --discard-untrimmed '
                    f'--revcomp -o {outputfile} {inputfile} --report minimal')
        else:
            cutcommand.append(
                f'{cutadaptlocation} -g {barcode5}{primer5} -O 17 -j 0 -m {minlen} --discard-untrimmed '
                f'--revcomp -o {outputfile} {inputfile} --report minimal')
    else:  # no primers, adapters, or trimming
        cutcommand.append(f'{cutadaptlocation} -j 0 -m {minlen} -o {outputfile} {inputfile} --report minimal')

    print(f'cutting adapters/primers/barcods from reads using cutadapt. Writting output to ' + colorama.Fore.YELLOW +
          f'{outputfile}')
    for command in cutcommand:
        print(colorama.Fore.CYAN + f'{command}' + colorama.Style.RESET_ALL)
        message.append(f'cutting adapters/primers/barcods from reads using cutadapt. Writting output to {outputfile}')
        message.append(f'{command}')
        cutadapt = runbin.Command(command)
        run = cutadapt.run(timeout=20000)
        print(run[1].decode())
        print(colorama.Fore.RED + f'{run[2].decode()}' + colorama.Style.RESET_ALL)
        message.append(run[1].decode())
        message.append(f'{run[2].decode()}')
    for file in tempfiles:
        try:
            os.remove(file)
        except:
            print(colorama.Fore.RED + f"couldn't remove " + colorama.Fore.YELLOW + f"{file}" + colorama.Style.RESET_ALL)
            message.append(f"couldn't remove {file}")
    return "\n".join(message)


def randomize(filename, format='fasta'):
    seqs = []
    message = []
    print(f'reading ' + colorama.Fore.YELLOW + f'{filename}' + colorama.Style.RESET_ALL)
    message.append(f'reading ' + f'{filename}')
    for record in Bio.SeqIO.parse(filename, format):
        randseq = ""
        for i in range(len(record.seq[:])):
            randseq = randseq + random.choice("ACTG")
        record.seq = Bio.Seq.Seq(randseq)
        print(
            colorama.Fore.MAGENTA + 'randomizing records:' + colorama.Fore.BLUE +
            f' {record.seq[:20]}...{record.seq[-20:]}' + colorama.Fore.MAGENTA + f' sequnce number {len(seqs):,}' +
            colorama.Style.RESET_ALL, end="\r")
        seqs.append(record)
    print(f'\rrewriting' + colorama.Fore.YELLOW + f' {filename}' + colorama.Style.RESET_ALL)
    message.append(f'\rrewriting' + f' {filename}')
    Bio.SeqIO.write(seqs, filename, format)
    return message


if __name__ == "__main__":

    filelist = ("../../../../mnt/c/Users/Bryan.Jones/Documents/SAMPL05.fastq",)
    '''filelist=("ILM170_04x07x2019_CL_BMO01GW_CL0174u01_cPCR_LMPCR_CovarisLM_Sample1_24x04x2019_TcellgDNA_ILM170_ILM170_CL0175u01_1000_MiS5TXIR4x159_AGTATCTCGT_GGGTT
    CCGCCGGATGGC_hg_0_CCTAACTGCTGTGCCACT_TCTACTGAGTGA_TAGTCACT.fastq",
    "ILM170_04x07x2019_CL_BMO01GW_CL0174u02_cPCR_LMPCR_CovarisLM_Sample1_24x04x2019_TcellgDNA_ILM170_ILM170_CL0175u02_1000_MiS5TXIR4x159_AGTATCTCGT_GGGTTCCGCCGGATGGC_hg_0_CCTAACTGCTGTGCCACT_TGCATCTAGCTC_TAGGAGCT.fastq",
    "ILM170_04x07x2019_CL_BMO01GW_CL0174u03_cPCR_LMPCR_CovarisLM_Sample1_24x04x2019_TcellgDNA_ILM170_ILM170_CL0175u03_1000_MiS5TXIR4x159_AGTATCTCGT_GGGTTCCGCCGGATGGC_hg_0_CCTAACTGCTGTGCCACT_TGTAGTCTACTG_TAGCAGTA.fastq",
    "ILM170_04x07x2019_CL_BMO01GW_CL0174u04_cPCR_LMPCR_CovarisLM_Sample2_24x04x2019_TcellgDNA_ILM170_ILM170_CL0175u04_1000_MiS5TXIR4x160_ATCTGCGACG_GGGTTCCGCCGGATGGC_hg_0_CCTAACTGCTGTGCCACT_ATCATCACACTC_TAGGAGTG.fastq",
    "ILM170_04x07x2019_CL_BMO01GW_CL0174u05_cPCR_LMPCR_CovarisLM_Sample2_24x04x2019_TcellgDNA_ILM170_ILM170_CL0175u05_1000_MiS5TXIR4x160_ATCTGCGACG_GGGTTCCGCCGGATGGC_hg_0_CCTAACTGCTGTGCCACT_CGTGCATAGCTG_TAGCAGCT.fastq",
    "ILM170_04x07x2019_CL_BMO01GW_CL0174u06_cPCR_LMPCR_CovarisLM_Sample2_24x04x2019_TcellgDNA_ILM170_ILM170_CL0175u06_1000_MiS5TXIR4x160_ATCTGCGACG_GGGTTCCGCCGGATGGC_hg_0_CCTAACTGCTGTGCCACT_TGCTATACGTGC_TAGGCACG.fastq",
    "ILM170_04x07x2019_CL_BMO01GW_CL0174u07_cPCR_LMPCR_CovarisLM_Sample3_24x04x2019_TcellgDNA_ILM170_ILM170_CL0175u07_1000_MiS5TXIR4x161_CTCTCTGATG_GGGTTCCGCCGGATGGC_hg_0_CCTAACTGCTGTGCCACT_CTGTCTGACGAG_TAGCTCGT.fastq",
    "ILM170_04x07x2019_CL_BMO01GW_CL0174u08_cPCR_LMPCR_CovarisLM_Sample3_24x04x2019_TcellgDNA_ILM170_ILM170_CL0175u08_1000_MiS5TXIR4x161_CTCTCTGATG_GGGTTCCGCCGGATGGC_hg_0_CCTAACTGCTGTGCCACT_TATAGTAGTCTC_TAGGAGAC.fastq",
    "ILM170_04x07x2019_CL_BMO01GW_CL0174u09_cPCR_LMPCR_CovarisLM_Sample3_24x04x2019_TcellgDNA_ILM170_ILM170_CL0175u09_1000_MiS5TXIR4x161_CTCTCTGATG_GGGTTCCGCCGGATGGC_hg_0_CCTAACTGCTGTGCCACT_CTGCGTGACAGC_TAGGCTGT.fastq",
    "ILM170_04x07x2019_CL_BMO01GW_CL0174u10_cPCR_LMPCR_CovarisLM_Sample4_24x04x2019_TcellgDNA_ILM170_ILM170_CL0175u10_1000_MiS5TXIR4x162_TATATAGCAC_GGGTTCCGCCGGATGGC_hg_0_CCTAACTGCTGTGCCACT_CATGTAGAGACT_TAGAGTCT.fastq",
    "ILM170_04x07x2019_CL_BMO01GW_CL0174u11_cPCR_LMPCR_CovarisLM_Sample4_24x04x2019_TcellgDNA_ILM170_ILM170_CL0175u11_1000_MiS5TXIR4x162_TATATAGCAC_GGGTTCCGCCGGATGGC_hg_0_CCTAACTGCTGTGCCACT_CTCAGAGATGAT_TAGATCAT.fastq",
    "ILM170_04x07x2019_CL_BMO01GW_CL0174u12_cPCR_LMPCR_CovarisLM_Sample4_24x04x2019_TcellgDNA_ILM170_ILM170_CL0175u12_1000_MiS5TXIR4x162_TATATAGCAC_GGGTTCCGCCGGATGGC_hg_0_CCTAACTGCTGTGCCACT_AGTCTCAGCACA_TAGTGTGC.fastq",
    "ILM170_04x07x2019_CL_BMO01GW_CL0174u13_cPCR_LMPCR_CovarisLM_Plasmidm995_0_Plasmid_ILM170_ILM170_CL0175u13_1_MiS5TXIR4x163_CTCACGATCT_GGGTTCCGCCGGATGGC_Ctrl_0_CCTAACTGCTGTGCCACT_TCAGCGATCGAT_TAGATCGATCGCTGAC.fastq",
    "ILM170_04x07x2019_CL_BMO01GW_CL0174u14_cPCR_LMPCR_CovarisLM_hgDNA_0_PBMC_ILM170_ILM170_CL0175u14_1000_MiS5TXIR4x164_TACTCTGCGT_GGGTTCCGCCGGATGGC_hg_Ctrl_CCTAACTGCTGTGCCACT_TCTGCGAGAGAG_TAGCTCTCTCGCAGACCTAAC.fastq")
    outputfiles=("01_full.fasta","02_full.fasta","03_full.fasta","04_full.fasta","05_full.fasta","06_full.fasta","07_full.fasta","08_full.fasta","09_full.fasta","10_full.fasta","11_full.fasta","12_full.fasta","13_full.fasta","14_full.fasta")
    ../../../../mnt/c/Users/Bryan.Jones/Documents/05.fasta",
    '''
    outputfiles = ("../../../../mnt/c/Users/Bryan.Jones/Documents/SAMPL05genomiconly.fasta",)
    for i in range(len(filelist)):
        QtoA(filelist[i], outputfiles[i])
    exit()
